"""Allow running as: python -m koodyna"""
import sys
from datetime import datetime, timedelta

from koodyna import BUILD_DATE, EXPIRE_DAYS

expire = datetime.strptime(BUILD_DATE, "%Y-%m-%d") + timedelta(days=EXPIRE_DAYS)
if datetime.now() > expire:
    print(f"This build expired on {expire.strftime('%Y-%m-%d')}.")
    print("Please download the latest version.")
    sys.exit(1)

from koodyna.cli import main

main()
