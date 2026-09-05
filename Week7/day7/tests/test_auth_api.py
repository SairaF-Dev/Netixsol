from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import bcrypt
from fastapi.testclient import TestClient

from web_api.app import create_app
from web_api.auth import AuthIdentity, AuthService, DuplicateRegistration, InvalidCredentials
from web_api.services import WebServices


A, B = str(uuid4()), str(uuid4())


class Customers:
    def __init__(self):
        self.records = {A: SimpleNamespace(customer_id=A, full_name="Alice", email="a@example.com", phone_normalized="+923001111111"), B: SimpleNamespace(customer_id=B, full_name="Bob", email="b@example.com", phone_normalized="+923002222222")}
        self.preferences = {key: SimpleNamespace(customer_id=key, city="Lahore", area=None, budget_min=None, budget_max=50_000_000, bedrooms=None, property_type=None, purpose=None, amenities=[]) for key in self.records}
    def resolve_for_customer_id(self, customer_id): return SimpleNamespace(customer=self.records.get(customer_id), preferences=self.preferences.get(customer_id))
    def update_preferences(self, customer_id, updates):
        for key,value in updates.items(): setattr(self.preferences[customer_id],key,value)
        return self.preferences[customer_id]


class Props:
    def list_available_cities(self): return ["Lahore"]
    def search(self, **kwargs): return []
    def get_property(self, property_id): return None


class Interactions: pass
class Ranker:
    def rank(self, rows, profile): return rows
class ML:
    mode="off"
    def rank_properties(self, rows, profile): return rows
    def health(self): return {"mode":"off","loaded":False}
class Appointments:
    async def request(self,*args,**kwargs): return 200,{"ok":True}


class FakeAuth:
    def __init__(self):
        self.identities={"token-a":AuthIdentity("ua",A,"Alice","a@example.com","+923001111111"),"token-b":AuthIdentity("ub",B,"Bob","b@example.com","+923002222222")}; self.logged_out=[]
        self.repository=SimpleNamespace(owns_appointment=lambda *x:False,own_appointment=lambda *x:None)
    def authenticate(self,token): return self.identities.get(token)
    def register(self,*args): return "token-a",datetime.now(timezone.utc)+timedelta(hours=1),self.identities["token-a"]
    def login(self,email,password):
        if password!="CorrectPass1": raise InvalidCredentials()
        return "token-a",datetime.now(timezone.utc)+timedelta(hours=1),self.identities["token-a"]
    def logout(self,token): self.logged_out.append(token)


def client():
    auth=FakeAuth(); services=WebServices(Customers(),Props(),Interactions(),Ranker(),ML(),Appointments(),auth_service=auth)
    return TestClient(create_app(services)),auth


def test_register_sets_httponly_cookie_and_exposes_no_hash():
    c,_=client(); response=c.post("/api/auth/register",json={"full_name":"Alice","email":"a@example.com","phone":"03001111111","password":"CorrectPass1"})
    assert response.status_code==201 and "HttpOnly" in response.headers["set-cookie"]
    assert "password" not in response.text and "hash" not in response.text


def test_login_success_failure_me_persistence_and_logout():
    c,auth=client(); assert c.post("/api/auth/login",json={"email":"a@example.com","password":"wrong"}).status_code==401
    assert c.post("/api/auth/login",json={"email":"a@example.com","password":"CorrectPass1"}).status_code==200
    assert c.get("/api/auth/me").json()["customer_id"]==A
    assert c.post("/api/auth/logout").status_code==204
    assert auth.logged_out==["token-a"]
    assert c.get("/api/auth/me").status_code==401


def test_protected_routes_require_authentication():
    c,_=client();
    assert c.get(f"/api/customers/{A}/preferences").status_code==401
    assert c.post(f"/api/customers/{A}/recommendations",json={}).status_code==401
    assert c.post("/api/interactions",json={"customer_id":A,"property_id":"P1","action":"liked","recommendation_session_id":str(uuid4())}).status_code==401


def test_user_a_cannot_access_user_b_customer_routes():
    c,_=client(); c.cookies.set("sara_session","token-a")
    assert c.get(f"/api/customers/{B}/preferences").status_code==403
    assert c.post(f"/api/customers/{B}/recommendations",json={}).status_code==403
    assert c.post("/api/interactions",json={"customer_id":B,"property_id":"P1","action":"liked","recommendation_session_id":str(uuid4())}).status_code==403


def test_user_cannot_mutate_unowned_appointment():
    c,_=client(); c.cookies.set("sara_session","token-a"); appointment_id=str(uuid4())
    assert c.patch(f"/api/appointments/{appointment_id}/reschedule",json={"starts_at":"2030-01-01T10:00:00+05:00"}).status_code==404
    assert c.delete(f"/api/appointments/{appointment_id}").status_code==404


def test_invalid_or_expired_session_rejected():
    c,_=client(); c.cookies.set("sara_session","expired-or-invalid")
    assert c.get("/api/auth/me").status_code==401


def test_me_preferences_derive_customer_from_cookie():
    c,_=client(); c.cookies.set("sara_session","token-a")
    assert c.get("/api/me/preferences").json()["customer_id"]==A
    assert c.patch("/api/me/preferences",json={"area":"DHA"}).json()["area"]=="DHA"


class Repo:
    def __init__(self): self.users={}; self.hash_value=""; self.sessions={}
    def get_user_by_email(self,email): return self.users.get(email)
    def create_user(self,customer_id,email,password_hash): self.hash_value=password_hash; self.users[email]=("u",customer_id,email,password_hash); return "u"
    def create_session(self,user_id,digest,expires): self.sessions[digest]=AuthIdentity(user_id,A,"Alice","a@example.com",None)
    def identity_for_digest(self,digest): return self.sessions.get(digest)
    def delete_session(self,digest): self.sessions.pop(digest,None)


def test_password_is_bcrypt_hashed_and_existing_customer_is_mapped():
    repo=Repo(); customers=SimpleNamespace(create_or_get_test_customer=lambda **kwargs:SimpleNamespace(customer=SimpleNamespace(customer_id=A,full_name="Alice",phone_normalized="+92300")))
    service=AuthService(repo,customers); token,_,identity=service.register("Alice","a@example.com","0300","CorrectPass1")
    assert repo.hash_value!="CorrectPass1" and bcrypt.checkpw(b"CorrectPass1",repo.hash_value.encode())
    assert identity.customer_id==A and service.authenticate(token).customer_id==A


def test_duplicate_registration_is_rejected_before_customer_mutation():
    repo=Repo(); repo.users["a@example.com"]=("u",A,"a@example.com",bcrypt.hashpw(b"CorrectPass1",bcrypt.gensalt()).decode())
    customers=SimpleNamespace(create_or_get_test_customer=lambda **kwargs:(_ for _ in ()).throw(AssertionError("must not mutate")))
    try: AuthService(repo,customers).register("Alice","a@example.com","0300","CorrectPass1")
    except DuplicateRegistration: pass
    else: raise AssertionError("duplicate registration accepted")
