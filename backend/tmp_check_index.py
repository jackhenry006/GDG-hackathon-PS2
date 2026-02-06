import time
import sys
sys.path.append('.')
import embed
print('documents:', len(embed.documents))
try:
    print('faiss ntotal:', embed.index.ntotal)
except Exception as e:
    print('index error', e)
print('model device:', getattr(embed.model, 'device', 'unknown'))
