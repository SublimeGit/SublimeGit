# coding: utf-8
from itertools import islice


def fletcher16(data):
    s1, s2 = 0, 0

    for i in data:
        s1 = (s1 + ord(i)) % 255
        s2 = (s1 + s2) % 255

    return (s2 << 8) | s1


def fletcher32(data):
    sum1, sum2 = 0, 0

    for i in data:
        sum1 = (sum1 + (ord(i) & 0xFF)) % 0xFFFF
        sum2 = (sum1 + sum2) % 0xFFFF

    return (sum2 << 16) | sum1


def license_keys(data):
    i = 0
    s1, s2 = 0, 0
    while True:
        s1 = (s1 + (ord(data[i]) & 0xFF)) % 0xFFFF
        s2 = (s1 + s2) % 0xFFFF
        data += "%x" % ((s2 << 16) | s1)
        i += 1
        if i > 100 and i % 8 == 0:
            yield data[-30:] + "%x" % (((i / 8) ^ 0xff) - 8)


def check_license(data, key):
    i = 0
    s1, s2 = 0, 0
    try:
        c = ((int(key[-2:], 16) + 8) ^ 0xff) * 8
    except ValueError:
        return False
    while i <= 1848:
        s1 = (s1 + (ord(data[i]) & 0xff)) % 0xffff
        s2 = (s1 + s2) % 0xffff
        data += "%x" % ((s2 << 16) | s1)
        i += 1
        if i == c and data[-30:] == key[:-2]:
            return True
    return False


if __name__ == '__main__':
    e = 'michael.pedersen@steelseries.com'
    keys = list(islice(license_keys(e), 219))

    import time

    for i, k in enumerate(keys):
        s = time.time()
        print "%s - %s: %s in %.5f ms" % (i, k, check_license(e, k), (time.time() - s) * 1000)
