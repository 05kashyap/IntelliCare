# Import Guard and Validator
from guardrails.hub import ShieldGemma2B
from guardrails import Guard, OnFailAction

guard_1 = Guard().use(
    ShieldGemma2B, 
    policies=[ShieldGemma2B.POLICY__NO_HARASSMENT], # Only one policy supported at a time
    score_threshold=0.5,
    on_fail=OnFailAction.EXCEPTION
)

guard_2 = Guard().use(
    ShieldGemma2B,
    policies=[ShieldGemma2B.POLICY__NO_DANGEROUS_CONTENT],
    score_thresold=0.5,
    on_fail=OnFailAction.EXCEPTION
    
)

