"""One-command integrated startup: python -m src.support.run."""
import json
import os
import secrets

from dotenv import load_dotenv


def main():
    load_dotenv()
    os.environ['SUPPORT_MODE']='integrated'
    os.environ.setdefault('SUPPORT_PRODUCT_STORE','sqlite')
    # Offline documents are explicit in launch output. Use atlas for vector RAG.
    os.environ.setdefault('SUPPORT_RAG_MODE','files')
    if not os.getenv('SUPPORT_ACCOUNTS'):
        codes={secrets.token_urlsafe(12):{'tenant_id':tenant,'actor_id':'owner_'+tenant,'role':'owner'} for tenant in ['tenant_a','tenant_b']}
        os.environ['SUPPORT_ACCOUNTS']=json.dumps(codes)
        print('Temporary login codes (valid for this server run):',flush=True)
        for code,identity in codes.items(): print(identity['tenant_id']+': '+code,flush=True)
    from src.backend.product import configured_state
    state=configured_state()
    for tenant in ['tenant_a','tenant_b']: state.initialize(tenant)
    print('Product store:',os.environ['SUPPORT_PRODUCT_STORE'],'| RAG:',os.environ['SUPPORT_RAG_MODE'],flush=True)
    print('Gemma:', 'hosted API' if os.getenv('GEMINI_API_KEY') else 'local Ollama (must be running)',flush=True)
    import uvicorn
    uvicorn.run('src.support.app:app',host='127.0.0.1',port=int(os.getenv('SUPPORT_PORT','8000')))


if __name__=='__main__': main()
