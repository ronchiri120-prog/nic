"""payments/mpesa.py — Safaricom Daraja API Integration"""
import requests
import base64
import json
from datetime import datetime
from django.conf import settings
import logging

logger = logging.getLogger('apps')

SANDBOX_BASE = 'https://sandbox.safaricom.co.ke'
PROD_BASE    = 'https://api.safaricom.co.ke'


def _base_url():
    return SANDBOX_BASE if settings.MPESA_ENV == 'sandbox' else PROD_BASE


def get_access_token():
    """Fetch OAuth access token from Daraja."""
    url = f'{_base_url()}/oauth/v1/generate?grant_type=client_credentials'
    creds = base64.b64encode(
        f'{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}'.encode()
    ).decode()
    resp = requests.get(url, headers={'Authorization': f'Basic {creds}'}, timeout=10)
    resp.raise_for_status()
    return resp.json()['access_token']


def get_stk_password():
    """Generate STK push password (Base64 of Shortcode+Passkey+Timestamp)."""
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    raw = f'{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{ts}'
    return base64.b64encode(raw.encode()).decode(), ts


def initiate_stk_push(phone: str, amount: float, account_ref: str, description: str = 'Loan Repayment') -> dict:
    """
    Initiates an STK Push (Lipa Na M-Pesa Online) for collections.

    Args:
        phone:        Customer phone in 254XXXXXXXXX format
        amount:       Amount in KES
        account_ref:  Loan ID or account reference
        description:  Transaction description
    Returns:
        Daraja API response dict
    """
    token    = get_access_token()
    password, timestamp = get_stk_password()

    payload = {
        'BusinessShortCode': settings.MPESA_SHORTCODE,
        'Password':          password,
        'Timestamp':         timestamp,
        'TransactionType':   'CustomerPayBillOnline',
        'Amount':            int(amount),
        'PartyA':            phone,
        'PartyB':            settings.MPESA_SHORTCODE,
        'PhoneNumber':       phone,
        'CallBackURL':       settings.MPESA_CALLBACK_URL,
        'AccountReference':  account_ref,
        'TransactionDesc':   description,
    }

    url = f'{_base_url()}/mpesa/stkpush/v1/processrequest'
    resp = requests.post(
        url,
        json=payload,
        headers={'Authorization': f'Bearer {token}'},
        timeout=15,
    )
    data = resp.json()
    logger.info(f'STK Push → {phone} KES {amount} | Response: {data}')
    return data


def initiate_b2c(phone: str, amount: float, loan_id: str, remarks: str = 'Loan Disbursement') -> dict:
    """
    Initiates a B2C payment (disbursement to customer).

    Args:
        phone:    Customer phone in 254XXXXXXXXX format
        amount:   Amount in KES
        loan_id:  Loan reference
        remarks:  Optional remarks
    Returns:
        Daraja API response dict
    """
    token = get_access_token()

    payload = {
        'InitiatorName':      'QuickLenderAPI',
        'SecurityCredential': settings.MPESA_PASSKEY,  # Should be encrypted credential in prod
        'CommandID':          'BusinessPayment',
        'Amount':             int(amount),
        'PartyA':             settings.MPESA_SHORTCODE,
        'PartyB':             phone,
        'Remarks':            remarks,
        'QueueTimeOutURL':    settings.MPESA_CALLBACK_URL + 'b2c/timeout/',
        'ResultURL':          settings.MPESA_CALLBACK_URL + 'b2c/result/',
        'Occasion':           loan_id,
    }

    url = f'{_base_url()}/mpesa/b2c/v1/paymentrequest'
    resp = requests.post(
        url,
        json=payload,
        headers={'Authorization': f'Bearer {token}'},
        timeout=15,
    )
    data = resp.json()
    logger.info(f'B2C → {phone} KES {amount} | Loan: {loan_id} | Response: {data}')
    return data


def query_stk_status(checkout_request_id: str) -> dict:
    """Query the status of an STK push transaction."""
    token    = get_access_token()
    password, timestamp = get_stk_password()

    payload = {
        'BusinessShortCode': settings.MPESA_SHORTCODE,
        'Password':          password,
        'Timestamp':         timestamp,
        'CheckoutRequestID': checkout_request_id,
    }
    url = f'{_base_url()}/mpesa/stkpushquery/v1/query'
    resp = requests.post(
        url,
        json=payload,
        headers={'Authorization': f'Bearer {token}'},
        timeout=10,
    )
    return resp.json()
