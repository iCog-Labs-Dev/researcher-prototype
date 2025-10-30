import hmac, hashlib, time, struct

email = "YOUR_EMAIL_HERE"
secret = email + "HENNGECHALLENGE004"

def generate_totp(secret, digits=10, timestep=30):
    key = secret.encode()
    counter = int(time.time() // timestep)
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha512).digest()
    o = h[-1] & 0x0F
    code = (struct.unpack(">I", h[o:o+4])[0] & 0x7FFFFFFF) % (10**digits)
    return str(code).zfill(digits)

totp = generate_totp(secret)
print(totp)
