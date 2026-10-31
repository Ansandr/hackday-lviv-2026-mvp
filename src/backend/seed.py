"""python -m src.backend.seed [--reset]; only touches the two mock tenant aggregates."""
import sys
from dotenv import load_dotenv
from .product import configured_state


def main():
    load_dotenv()
    state=configured_state()
    for tenant in ('tenant_a','tenant_b'):
        state.initialize(tenant,reset='--reset' in sys.argv)
        print('Seed ready:',tenant)


if __name__=='__main__':
    main()
