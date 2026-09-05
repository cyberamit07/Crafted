from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from .models import (
    User, Deal, DealParticipant, DealAgreement,
    Payment, Refund, Vouch, Escrower, Admin,
    Dispute, Log, Setting, DealStatus, PaymentMethod, DisputeStatus
)
from config import config

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_or_create(self, telegram_id: int, username: str = None, 
                           first_name: str = None, last_name: str = None) -> User:
        """Get or create user"""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            self.session.add(user)
            await self.session.flush()
        
        # Update username if changed
        elif username and user.username != username:
            user.username = username
            await self.session.flush()
        
        return user
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID"""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by database ID"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def is_banned(self, telegram_id: int) -> bool:
        """Check if user is banned"""
        user = await self.get_by_telegram_id(telegram_id)
        return user.is_banned if user else False
    
    async def ban_user(self, telegram_id: int) -> bool:
        """Ban a user"""
        user = await self.get_by_telegram_id(telegram_id)
        if user and not user.is_banned:
            user.is_banned = True
            await self.session.flush()
            return True
        return False
    
    async def unban_user(self, telegram_id: int) -> bool:
        """Unban a user"""
        user = await self.get_by_telegram_id(telegram_id)
        if user and user.is_banned:
            user.is_banned = False
            await self.session.flush()
            return True
        return False
    
    async def get_all_users(self) -> List[User]:
        """Get all users"""
        result = await self.session.execute(select(User))
        return result.scalars().all()
    
    async def get_user_count(self) -> int:
        """Get total user count"""
        result = await self.session.execute(select(func.count(User.id)))
        return result.scalar() or 0

class DealRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_deal(self, buyer_id: int, seller_id: int, item: str,
                          amount: float, payment_method: PaymentMethod,
                          holding_time: str, terms: str = None) -> Deal:
        """Create a new deal"""
        # Generate deal ID
        count_result = await self.session.execute(select(func.count(Deal.id)))
        count = count_result.scalar() or 0
        deal_id = f"{config.DEAL_ID_PREFIX}-{count + 1:06d}"
        
        deal = Deal(
            deal_id=deal_id,
            item=item,
            amount=amount,
            payment_method=payment_method,
            holding_time=holding_time,
            terms=terms,
            status=DealStatus.WAITING_FOR_AGREEMENT
        )
        self.session.add(deal)
        await self.session.flush()
        
        # Add participants
        participant = DealParticipant(
            deal_id=deal.id,
            buyer_id=buyer_id,
            seller_id=seller_id
        )
        self.session.add(participant)
        await self.session.flush()
        
        return deal
    
    async def get_by_id(self, deal_id: str) -> Optional[Deal]:
        """Get deal by deal ID"""
        result = await self.session.execute(
            select(Deal).where(Deal.deal_id == deal_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_db_id(self, deal_id: int) -> Optional[Deal]:
        """Get deal by database ID"""
        result = await self.session.execute(
            select(Deal).where(Deal.id == deal_id)
        )
        return result.scalar_one_or_none()
    
    async def update_status(self, deal_id: int, status: DealStatus) -> bool:
        """Update deal status"""
        deal = await self.get_by_db_id(deal_id)
        if deal:
            # Validate status transition
            if self._is_valid_transition(deal.status, status):
                deal.status = status
                if status == DealStatus.COMPLETED:
                    deal.completed_at = datetime.utcnow()
                elif status == DealStatus.REFUNDED:
                    deal.refunded_at = datetime.utcnow()
                await self.session.flush()
                return True
        return False
    
    def _is_valid_transition(self, current: DealStatus, new: DealStatus) -> bool:
        """Validate status transitions"""
        valid_transitions = {
            DealStatus.DRAFT: [DealStatus.WAITING_FOR_AGREEMENT, DealStatus.CANCELLED],
            DealStatus.WAITING_FOR_AGREEMENT: [DealStatus.AGREED_WAITING_PAYMENT, DealStatus.CANCELLED],
            DealStatus.AGREED_WAITING_PAYMENT: [DealStatus.ACTIVE, DealStatus.CANCELLED],
            DealStatus.ACTIVE: [DealStatus.DISPUTED, DealStatus.COMPLETED, DealStatus.REFUND_REQUESTED],
            DealStatus.DISPUTED: [DealStatus.ACTIVE, DealStatus.REFUNDED, DealStatus.COMPLETED],
            DealStatus.REFUND_REQUESTED: [DealStatus.REFUNDED, DealStatus.ACTIVE],
            DealStatus.REFUNDED: [],
            DealStatus.COMPLETED: [],
            DealStatus.CANCELLED: []
        }
        return new in valid_transitions.get(current, [])
    
    async def get_deals_by_user(self, user_id: int, status: Optional[DealStatus] = None) -> List[Deal]:
        """Get deals for a user"""
        query = select(Deal).join(DealParticipant).where(
            or_(
                DealParticipant.buyer_id == user_id,
                DealParticipant.seller_id == user_id
            )
        )
        if status:
            query = query.where(Deal.status == status)
        query = query.order_by(desc(Deal.created_at))
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_deals_by_escrower(self, escrower_id: int) -> List[Deal]:
        """Get deals assigned to escrower"""
        result = await self.session.execute(
            select(Deal).where(Deal.escrower_id == escrower_id)
            .order_by(desc(Deal.created_at))
        )
        return result.scalars().all()
    
    async def get_deal_participants(self, deal_id: int) -> Optional[DealParticipant]:
        """Get participants for a deal"""
        result = await self.session.execute(
            select(DealParticipant).where(DealParticipant.deal_id == deal_id)
        )
        return result.scalar_one_or_none()
    
    async def set_agreement(self, deal_id: int, user_id: int, agreed: bool) -> bool:
        """Set agreement for a participant"""
        participant = await self.get_deal_participants(deal_id)
        if not participant:
            return False
        
        if participant.buyer_id == user_id:
            participant.buyer_agreed = agreed
            participant.buyer_agreed_at = datetime.utcnow() if agreed else None
        elif participant.seller_id == user_id:
            participant.seller_agreed = agreed
            participant.seller_agreed_at = datetime.utcnow() if agreed else None
        else:
            return False
        
        await self.session.flush()
        
        # Check if both agreed
        if participant.buyer_agreed and participant.seller_agreed:
            await self.update_status(deal_id, DealStatus.AGREED_WAITING_PAYMENT)
        
        return True
    
    async def assign_escrower(self, deal_id: int, escrower_id: int) -> bool:
        """Assign escrower to deal"""
        deal = await self.get_by_db_id(deal_id)
        if deal:
            deal.escrower_id = escrower_id
            await self.session.flush()
            return True
        return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get deal statistics"""
        stats = {}
        
        # Count by status
        for status in DealStatus:
            result = await self.session.execute(
                select(func.count(Deal.id)).where(Deal.status == status)
            )
            stats[f'{status.value.lower()}_count'] = result.scalar() or 0
        
        # Total deals
        result = await self.session.execute(select(func.count(Deal.id)))
        stats['total_deals'] = result.scalar() or 0
        
        # Volume by payment method
        for method in PaymentMethod:
            result = await self.session.execute(
                select(func.sum(Deal.amount))
                .where(and_(
                    Deal.payment_method == method,
                    Deal.status.in_([DealStatus.COMPLETED, DealStatus.ACTIVE])
                ))
            )
            stats[f'{method.value.lower()}_volume'] = result.scalar() or 0.0
        
        return stats

class EscrowerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add_escrower(self, user_id: int, added_by: int) -> bool:
        """Add user as escrower"""
        # Check if already exists
        result = await self.session.execute(
            select(Escrower).where(Escrower.user_id == user_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            if not existing.is_active:
                existing.is_active = True
                existing.removed_at = None
                await self.session.flush()
                return True
            return False
        
        escrower = Escrower(
            user_id=user_id,
            added_by=added_by,
            is_active=True
        )
        self.session.add(escrower)
        await self.session.flush()
        return True
    
    async def remove_escrower(self, user_id: int) -> bool:
        """Remove escrower"""
        result = await self.session.execute(
            select(Escrower).where(Escrower.user_id == user_id)
        )
        escrower = result.scalar_one_or_none()
        
        if escrower and escrower.is_active:
            escrower.is_active = False
            escrower.removed_at = datetime.utcnow()
            await self.session.flush()
            return True
        return False
    
    async def is_escrower(self, user_id: int) -> bool:
        """Check if user is an active escrower"""
        result = await self.session.execute(
            select(Escrower).where(
                and_(Escrower.user_id == user_id, Escrower.is_active == True)
            )
        )
        return result.scalar_one_or_none() is not None
    
    async def get_all_escrowers(self) -> List[Escrower]:
        """Get all active escrowers"""
        result = await self.session.execute(
            select(Escrower).where(Escrower.is_active == True)
            .join(User).order_by(User.username)
        )
        return result.scalars().all()
    
    async def get_escrower_count(self) -> int:
        """Get active escrower count"""
        result = await self.session.execute(
            select(func.count(Escrower.id)).where(Escrower.is_active == True)
        )
        return result.scalar() or 0

class AdminRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add_admin(self, user_id: int, added_by: int) -> bool:
        """Add user as admin"""
        result = await self.session.execute(
            select(Admin).where(Admin.user_id == user_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            if not existing.is_active:
                existing.is_active = True
                existing.removed_at = None
                await self.session.flush()
                return True
            return False
        
        admin = Admin(
            user_id=user_id,
            added_by=added_by,
            is_active=True
        )
        self.session.add(admin)
        await self.session.flush()
        return True
    
    async def remove_admin(self, user_id: int) -> bool:
        """Remove admin"""
        result = await self.session.execute(
            select(Admin).where(Admin.user_id == user_id)
        )
        admin = result.scalar_one_or_none()
        
        if admin and admin.is_active:
            admin.is_active = False
            admin.removed_at = datetime.utcnow()
            await self.session.flush()
            return True
        return False
    
    async def is_admin(self, user_id: int) -> bool:
        """Check if user is an active admin"""
        result = await self.session.execute(
            select(Admin).where(
                and_(Admin.user_id == user_id, Admin.is_active == True)
            )
        )
        return result.scalar_one_or_none() is not None
    
    async def get_all_admins(self) -> List[Admin]:
        """Get all active admins"""
        result = await self.session.execute(
            select(Admin).where(Admin.is_active == True)
            .join(User).order_by(User.username)
        )
        return result.scalars().all()
    
    async def get_admin_count(self) -> int:
        """Get active admin count"""
        result = await self.session.execute(
            select(func.count(Admin.id)).where(Admin.is_active == True)
        )
        return result.scalar() or 0

class LogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add_log(self, action: str, deal_id: str = None,
                     user_id: int = None, username: str = None,
                     details: str = None) -> Log:
        """Add a log entry"""
        log = Log(
            action=action,
            deal_id=deal_id,
            user_id=user_id,
            username=username,
            details=details
        )
        self.session.add(log)
        await self.session.flush()
        return log
    
    async def get_logs(self, limit: int = 50, offset: int = 0) -> List[Log]:
        """Get recent logs"""
        result = await self.session.execute(
            select(Log).order_by(desc(Log.created_at))
            .limit(limit).offset(offset)
        )
        return result.scalars().all()

class VouchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_vouch(self, deal_id: int, user_id: int, vouch_text: str) -> Vouch:
        """Create a vouch"""
        vouch = Vouch(
            deal_id=deal_id,
            user_id=user_id,
            vouch_text=vouch_text
        )
        self.session.add(vouch)
        await self.session.flush()
        return vouch
    
    async def mark_sent(self, vouch_id: int, message_id: int) -> bool:
        """Mark vouch as sent"""
        vouch = await self.get_by_id(vouch_id)
        if vouch:
            vouch.is_sent = True
            vouch.sent_at = datetime.utcnow()
            vouch.message_id = message_id
            await self.session.flush()
            return True
        return False
    
    async def get_by_id(self, vouch_id: int) -> Optional[Vouch]:
        """Get vouch by ID"""
        result = await self.session.execute(
            select(Vouch).where(Vouch.id == vouch_id)
        )
        return result.scalar_one_or_none()
    
    async def get_vouch_count(self) -> int:
        """Get total vouch count"""
        result = await self.session.execute(
            select(func.count(Vouch.id)).where(Vouch.is_sent == True)
        )
        return result.scalar() or 0

class DisputeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_dispute(self, deal_id: int, initiator_id: int,
                           reason: str) -> Dispute:
        """Create a dispute"""
        dispute = Dispute(
            deal_id=deal_id,
            initiator_id=initiator_id,
            reason=reason,
            status=DisputeStatus.OPEN
        )
        self.session.add(dispute)
        await self.session.flush()
        return dispute
    
    async def resolve_dispute(self, dispute_id: int, resolver_id: int,
                            resolution_notes: str, status: DisputeStatus = DisputeStatus.RESOLVED) -> bool:
        """Resolve a dispute"""
        result = await self.session.execute(
            select(Dispute).where(Dispute.id == dispute_id)
        )
        dispute = result.scalar_one_or_none()
        
        if dispute and dispute.status == DisputeStatus.OPEN:
            dispute.status = status
            dispute.resolved_at = datetime.utcnow()
            dispute.resolved_by = resolver_id
            dispute.resolution_notes = resolution_notes
            await self.session.flush()
            return True
        return False
    
    async def get_open_disputes(self) -> List[Dispute]:
        """Get all open disputes"""
        result = await self.session.execute(
            select(Dispute).where(Dispute.status == DisputeStatus.OPEN)
            .order_by(desc(Dispute.created_at))
        )
        return result.scalars().all()

class StatsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """Get global statistics"""
        stats = {}
        
        # User stats
        user_repo = UserRepository(self.session)
        stats['total_users'] = await user_repo.get_user_count()
        
        # Escrower stats
        escrower_repo = EscrowerRepository(self.session)
        stats['active_escrowers'] = await escrower_repo.get_escrower_count()
        
        # Admin stats
        admin_repo = AdminRepository(self.session)
        stats['admin_count'] = await admin_repo.get_admin_count()
        
        # Deal stats
        deal_repo = DealRepository(self.session)
        deal_stats = await deal_repo.get_stats()
        stats.update(deal_stats)
        
        # Vouch stats
        vouch_repo = VouchRepository(self.session)
        stats['vouch_count'] = await vouch_repo.get_vouch_count()
        
        return stats
