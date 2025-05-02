from decimal import Decimal
from user.models import VPNUser

def apply_payment(user: VPNUser, amount: Decimal):
    user.balance += amount
    user.save()

    if user.referred_by:
        bonus = amount * Decimal('0.10')
        user.referred_by.balance += bonus
        user.referred_by.save()

        user.got_referral_bonus = True
        user.save()
