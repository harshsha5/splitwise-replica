from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

class SplitType(Enum):
    EQUAL = "equal"
    CUSTOM = "custom"

@dataclass
class Participant:
    name: str
    amount_owed: float = 0.0
    amount_paid: float = 0.0

@dataclass
class Expense:
    id: str
    title: str
    amount: float
    paid_by: str  # Primary payer for display purposes
    participants: List[Participant]
    split_type: SplitType
    date: datetime
    category: Optional[str] = None
    external_payments: Dict[str, float] = None  # Payments from non-participants
    
    def __post_init__(self):
        if self.external_payments is None:
            self.external_payments = {}
    
    def calculate_splits(self):
        if self.split_type == SplitType.EQUAL:
            per_person = self.amount / len(self.participants)
            for participant in self.participants:
                participant.amount_owed = per_person
        # For CUSTOM splits, amounts should already be set by the caller
        # This method just ensures consistency
        
    def get_balance_summary(self) -> Dict[str, float]:
        balances = {}
        
        # Calculate net balance for each participant
        # Positive balance = person is owed money
        # Negative balance = person owes money
        for participant in self.participants:
            net_balance = participant.amount_paid - participant.amount_owed
            balances[participant.name] = net_balance
        
        # Include external payers (non-participants who paid)
        for payer_name, amount_paid in self.external_payments.items():
            balances[payer_name] = balances.get(payer_name, 0.0) + amount_paid
            
        return balances
    
    def set_payments(self, payments: Dict[str, float]):
        """Set who paid what amounts. payments is a dict of {name: amount_paid}"""
        # Reset external payments
        self.external_payments = {}
        
        # Set payments for participants
        for participant in self.participants:
            participant.amount_paid = payments.get(participant.name, 0.0)
        
        # Track payments from non-participants as external payments
        participant_names = {p.name for p in self.participants}
        for payer_name, amount_paid in payments.items():
            if payer_name not in participant_names and amount_paid > 0:
                self.external_payments[payer_name] = amount_paid
    
    def validate_payments(self) -> bool:
        """Check if total payments equal the expense amount"""
        total_paid = sum(p.amount_paid for p in self.participants) + sum(self.external_payments.values())
        return abs(total_paid - self.amount) < 0.01  # Allow for small rounding errors