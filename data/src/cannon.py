import random

cannon1 = 10
rate1 = 0.5
cannon2 = 30
rate2 = 0.3

cannon1_, cannon2_ = cannon1, cannon2

for _ in range(cannon1):
    if rate1 > random.random():
        cannon2_ -= 1
    if cannon2_ == 0:
        break
for _ in range(cannon2):
    if rate2 > random.random():
        cannon1_ -= 1
    if cannon1_ == 0:
        break
cannon1, cannon2 = cannon1_, cannon2_


print(cannon1, cannon2)
