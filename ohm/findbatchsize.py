import sys
from math import ceil

total = int(sys.argv[1])
relations = int(sys.argv[2])

candidates = []
for batchSize in range(1, 1001):
    nBatches = ceil(total/batchSize)
    if (nBatches-1)*batchSize < total-relations:
        candidates.append((batchSize, (nBatches-1)*batchSize))
candidates.sort(key=lambda a: a[1], reverse=True)
for batchSize, lastBatch in candidates[:10]:
    print(batchSize, lastBatch)

