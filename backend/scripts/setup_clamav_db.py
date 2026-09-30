import os

db_dir = r"C:\Users\kishu\tools\clamav\db"
os.makedirs(db_dir, exist_ok=True)

eicar = "X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
eicar_bytes = eicar.encode("ascii")
print(f"EICAR length: {len(eicar_bytes)}")

# ClamAV .ndb format: MalwareName:TargetType:Offset:HexSignature
sig_content = f"Win.Test.EICAR_HDB-1:0:*:{eicar_bytes.hex()}\n"

ndb_path = os.path.join(db_dir, "test.ndb")
with open(ndb_path, "w") as f:
    f.write(sig_content)

print(f"Successfully wrote {ndb_path} with {len(eicar_bytes)} bytes EICAR signature.")
