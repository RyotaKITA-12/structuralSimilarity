def function1(var1, var2, var3):
    if var1[var2] < var1[var3]:
        var1[var3], var1[var2] = var1[var2], var1[var3]
    return var1


# Exchange_sort
A = [3, 5, 1, 9, 7, 8, 5]
n = len(A)
for i in range(n):
    for j in range(i+1, n):
        A = function1(A, j, i)
print(A)

# BubbleSort
A = [3, 5, 1, 9, 7, 8, 5]
n = len(A)
for i in range(n-1):
    for j in range(n-1):
        A = function1(A, j+1, j)
print(A)
