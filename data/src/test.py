for i in range(n):
    for j in range(i+1, n):
        if A[j] < A[i]:
            A[i], A[j] = A[j], A[i]
for i in range(n-1):
    for j in range(n-1):
        if A[j+1] < A[j]:
            A[j], A[j+1] = A[j+1], A[j]
