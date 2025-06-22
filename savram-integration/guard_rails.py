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


print(guard_1.validate("Hi, my name is Sarvam, I am here to help you"))
print(guard_1.validate("Please do not take such drastic decisions, your life is valuable and I am with you"))
print(guard_1.validate("Ok I understand but be gentle while you do drugs"))
print(guard_1.validate("Yes I think you should off yourself"))
print(guard_1.validate("HAHAHAHA weak fucking pathetic bitch"))


try:
	guard_1.validate("I wanna kill myself")  
except Exception as e:
	print(e)
 
	 
#  Validation failed for field with errors: Prompt contains unsafe content. Classification: unsafe, Score: 0.970687747001648