import os
import re
import time
from pathlib import Path
import requests

HOST_URL = "http://localhost:8000"
EXAMPLES_FOLDER_ROOT = Path("examples") # adjust as needed

rag_a_query_1 = "Why did the dreamer in White Nights not like the yellow house?"
rag_a_query_2 = "Who was Matrona in White Nights?"
rag_b_query = "Who guided Dante through Inferno?"


def extract_id(msg: str) -> int:
    m = re.search(r"\((\d+)\)", msg)
    if not m:
        raise ValueError(f"Could not extract id from '{msg}'")
    return int(m.group(1))


def wait_for_documents_uploaded(token: str, rag_id: int, timeout=120):
    headers = {"Authorization": f"Bearer {token}"}
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(f"{HOST_URL}/rags/{rag_id}", headers=headers)
        if r.status_code == 200:
            j = r.json()
            docs = j.get("documents", [])
            if len(docs) > 0 and all(d.get("status") == "uploaded" for d in docs):
                return j
        time.sleep(5)
    raise TimeoutError("Timed out waiting for documents to be uploaded")


def wait_for_job_complete(token: str, job_id: int, timeout=120):
    headers = {"Authorization": f"Bearer {token}"}
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(f"{HOST_URL}/jobs/{job_id}", headers=headers)
        if r.status_code == 200:
            j = r.json()
            if j.get("status") == "completed":
                return j
        time.sleep(5)
    raise TimeoutError("Timed out waiting for job to complete")


def run_demo():
    # 1) create two users
    users = [
        {"username": "user1", "password": "pass1", "confirm_password": "pass1"},
        {"username": "user2", "password": "pass2", "confirm_password": "pass2"},
    ]
    for u in users:
        r = requests.post(f"{HOST_URL}/user/", json=u)
        print("create user ->", r.status_code, r.text)

    # 2) login both users
    tokens = {}
    for u in users:
        creds = {"username": u["username"], "password": u["password"]}
        r = requests.post(f"{HOST_URL}/user/login", json=creds)
        r.raise_for_status()
        tok = r.json()["token"]
        tokens[u["username"]] = tok
        print(f"logged in {u['username']}")

    # 3) create RAGs
    headers1 = {"Authorization": f"Bearer {tokens['user1']}"}
    headers2 = {"Authorization": f"Bearer {tokens['user2']}"}

    r = requests.post(f"{HOST_URL}/rags/", json={"name": "rag_a", "public": True}, headers=headers1)
    r.raise_for_status()
    rag_a_id = extract_id(r.text)
    print("created rag_a ->", rag_a_id)

    r = requests.post(f"{HOST_URL}/rags/", json={"name": "rag_b", "public": False}, headers=headers2)
    r.raise_for_status()
    rag_b_id = extract_id(r.text)
    print("created rag_b ->", rag_b_id)

    # 4) ingest documents sequentially using the examples folder
    # user1 -> rag_a
    rag_a_folder = EXAMPLES_FOLDER_ROOT / "rag_a"
    files_to_send = []
    file_objs = []
    for p in rag_a_folder.iterdir():
        f = open(p, "rb")
        file_objs.append(f)
        files_to_send.append(("files", (p.name, f, "text/plain")))

    r = requests.post(f"{HOST_URL}/rags/ingest/{rag_a_id}", files=files_to_send, headers=headers1)
    print("ingest rag_a ->", r.status_code, r.text)
    for f in file_objs:
        f.close()

    # wait for ingestion to finish
    print("waiting for rag_a documents to be uploaded...")
    wait_for_documents_uploaded(tokens["user1"], rag_a_id)
    print("rag_a ingestion completed")

    # user2 -> rag_b
    rag_b_folder = EXAMPLES_FOLDER_ROOT / "rag_b"
    files_to_send = []
    file_objs = []
    for p in rag_b_folder.iterdir():
        f = open(p, "rb")
        file_objs.append(f)
        files_to_send.append(("files", (p.name, f, "text/plain")))

    r = requests.post(f"{HOST_URL}/rags/ingest/{rag_b_id}", files=files_to_send, headers=headers2)
    print("ingest rag_b ->", r.status_code, r.text)
    for f in file_objs:
        f.close()

    print("waiting for rag_b documents to be uploaded...")
    wait_for_documents_uploaded(tokens["user2"], rag_b_id)
    print("rag_b ingestion completed")

    # 5) make queries
    # user1 queries rag_a (permitted)
    q = {"message": rag_a_query_1, "temperature": 0.3}
    r = requests.post(f"{HOST_URL}/rags/query/{rag_a_id}", json=q, headers=headers1)
    print("user1 query rag_a ->", r.status_code, r.text)
    if r.status_code == 200:
        job_id = r.json()["job_id"]
        job = wait_for_job_complete(tokens["user1"], job_id)
        print("job result:", job.get("response", ""))

    # user2 queries rag_b (permitted)
    q = {"message": rag_b_query, "temperature": 0.3}
    r = requests.post(f"{HOST_URL}/rags/query/{rag_b_id}", json=q, headers=headers2)
    print("user2 query rag_b ->", r.status_code, r.text)
    if r.status_code == 200:
        job_id = r.json()["job_id"]
        job = wait_for_job_complete(tokens["user2"], job_id)
        print("job result:", job.get("response", ""))

    # user1 queries rag_b (NOT permitted)
    q = {"message": "Can you read rag_b docs?", "temperature": 0.3}
    r = requests.post(f"{HOST_URL}/rags/query/{rag_b_id}", json=q, headers=headers1)
    print("user1 query rag_b (should be forbidden) ->", r.status_code, r.text)

    # user2 queries rag_a (public)
    q = {"message": rag_a_query_2, "temperature": 0.3}
    r = requests.post(f"{HOST_URL}/rags/query/{rag_a_id}", json=q, headers=headers2)
    print("user2 query rag_a ->", r.status_code, r.text)
    if r.status_code == 200:
        job_id = r.json()["job_id"]
        job = wait_for_job_complete(tokens["user2"], job_id)
        print("job result:", job.get("response", ""))


if __name__ == "__main__":
    run_demo()
