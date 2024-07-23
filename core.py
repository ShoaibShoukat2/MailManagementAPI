from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import requests
from dotenv import load_dotenv
import os


SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')

# Load environment variables from the .env file
load_dotenv()

app = FastAPI()




class DomainModel(BaseModel):
    domain: str

class EmailModel(BaseModel):
    from_email: str
    to_email: str
    subject: str
    content: str

def add_domain_to_sendgrid(domain: str):
    url = "https://api.sendgrid.com/v3/whitelabel/domains"
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "domain": domain,
        "automatic_security": True
    }
    response = requests.post(url, headers=headers, json=payload)
    return response.json()

def get_dns_records(domain_info):
    dns_records = []
    dns_info = domain_info.get('dns', {})
    for key, record in dns_info.items():
        dns_records.append({
            "type": record['type'],
            "name": record['host'],
            "content": record['data'],
            "ttl": 120  # Default TTL value
        })
    return dns_records

def verify_domain(domain_id):
    url = f"https://api.sendgrid.com/v3/whitelabel/domains/{domain_id}/validate"
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers)
    return response.json()

def send_email(api_key, from_email, to_email, subject, content):
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=content)
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        return response.status_code, response.body, response.headers
    except Exception as e:
        return str(e)



@app.post("/add-domain")
def add_domain(domain_model: DomainModel):
    domain_info = add_domain_to_sendgrid(domain_model.domain)
    if 'id' not in domain_info:
        raise HTTPException(status_code=400, detail=f"Error adding domain to SendGrid: {domain_info}")
    dns_records = get_dns_records(domain_info)
    return {"domain_info": domain_info, "dns_records": dns_records}

@app.post("/verify-domain/{domain_id}")
def verify_domain_endpoint(domain_id: int):
    verification_result = verify_domain(domain_id)
    if verification_result.get('valid', False):
        return {"message": "Domain verification successful!"}
    else:
        raise HTTPException(status_code=400, detail=f"Domain verification failed: {verification_result}")

@app.post("/send-email")
def send_email_endpoint(email_model: EmailModel):
    status_code, body, headers = send_email(SENDGRID_API_KEY, email_model.from_email, email_model.to_email, email_model.subject, email_model.content)
    if status_code == 202:
        return {"message": "Email sent successfully!", "status_code": status_code}
    else:
        raise HTTPException(status_code=400, detail=f"Error sending email: {body}")
    
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
    
    


