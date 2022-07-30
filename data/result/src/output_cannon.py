def function1(var2, var3, var4, var5):
    for var1 in range(var2):
        if var3 > var4.random():
            var5 -= 1
        if var5 == 0:
            break
    return var1, var2, var3, var4, var5

import random

cannon1 = 10
rate1 = 0.5
cannon2 = 30
rate2 = 0.3

cannon1_, cannon2_ = cannon1, cannon2

_, cannon1, rate1, random, cannon2_ = function1(cannon1, rate1, random, cannon2_)
_, cannon2, rate2, random, cannon1_ = function1(cannon2, rate2, random, cannon1_)
cannon1, cannon2 = cannon1_, cannon2_


print(cannon1, cannon2)
