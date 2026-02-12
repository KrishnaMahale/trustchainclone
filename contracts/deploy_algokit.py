"""
AlgoKit deployment script for TrustChain contribution contract.
Run from repo root: python contracts/deploy_algokit.py
Uses TEAL compiled from contribution_contract.py; requires CREATOR_MNEMONIC and REPUTATION_ASA_ID in env.
"""
import os
import sys

# Add parent for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Compile PyTeal first
from pathlib import Path

teal_dir = Path(__file__).parent / "teal"
teal_dir.mkdir(exist_ok=True)
approval_path = teal_dir / "contribution_approval.teal"
clear_path = teal_dir / "contribution_clear.teal"

if not approval_path.exists():
    import subprocess
    subprocess.run([sys.executable, str(Path(__file__).parent / "contribution_contract.py")], check=True)

from algosdk import account, mnemonic
from algosdk.v2client import algod
from algosdk.future import transaction
from algosdk import logic
import base64


def load_teal(path: Path) -> str:
    with open(path) as f:
        return f.read()


def deploy(
    creator_mnemonic: str,
    project_id: int,
    deadline_contribution_ts: int,
    deadline_voting_ts: int,
    weight_code: int,
    weight_time: int,
    weight_vote: int,
    reputation_asa_id: int,
    algod_url: str = "https://testnet-api.algonode.cloud",
    algod_token: str = "",
):
    """Deploy the contribution app to TestNet."""
    client = algod.AlgodClient(algod_token, algod_url)
    private_key = mnemonic.to_private_key(creator_mnemonic)
    sender = account.address_from_private_key(private_key)

    approval_teal = load_teal(approval_path)
    clear_teal = load_teal(clear_path)
    approval_result = client.compile(approval_teal)
    clear_result = client.compile(clear_teal)
    approval_binary = base64.b64decode(approval_result["result"])
    clear_binary = base64.b64decode(clear_result["result"])

    app_args = [
        project_id.to_bytes(8, "big"),
        deadline_contribution_ts.to_bytes(8, "big"),
        deadline_voting_ts.to_bytes(8, "big"),
        weight_code.to_bytes(8, "big"),
        weight_time.to_bytes(8, "big"),
        weight_vote.to_bytes(8, "big"),
        reputation_asa_id.to_bytes(8, "big"),
    ]
    params = client.suggested_params()
    txn = transaction.ApplicationCreateTxn(
        sender,
        params,
        transaction.OnComplete.NoOpOC,
        approval_binary,
        clear_binary,
        app_args=app_args,
    )
    signed = txn.sign(private_key)
    txid = client.send_transaction(signed)
    result = transaction.wait_for_confirmation(client, txid, 4)
    app_id = result["application-index"]
    app_address = logic.get_application_address(app_id)
    print(f"Deployed app_id={app_id} app_address={app_address}")
    return app_id, app_address


if __name__ == "__main__":
    import argparse
    from datetime import datetime

    parser = argparse.ArgumentParser()
    parser.add_argument("--creator-mnemonic", default=os.environ.get("CREATOR_MNEMONIC"), help="Creator 25-word mnemonic")
    parser.add_argument("--project-id", type=int, default=1)
    parser.add_argument("--deadline-contrib", type=int, default=int(datetime.utcnow().timestamp()) + 86400 * 14)
    parser.add_argument("--deadline-vote", type=int, default=int(datetime.utcnow().timestamp()) + 86400 * 21)
    parser.add_argument("--weight-code", type=int, default=40)
    parser.add_argument("--weight-time", type=int, default=30)
    parser.add_argument("--weight-vote", type=int, default=30)
    parser.add_argument("--rep-asa", type=int, default=int(os.environ.get("REPUTATION_ASA_ID", "0")))
    parser.add_argument("--algod-url", default=os.environ.get("ALGOD_URL", "https://testnet-api.algonode.cloud"))
    args = parser.parse_args()
    if not args.creator_mnemonic:
        print("Set CREATOR_MNEMONIC or --creator-mnemonic")
        sys.exit(1)
    deploy(
        args.creator_mnemonic,
        args.project_id,
        args.deadline_contrib,
        args.deadline_vote,
        args.weight_code,
        args.weight_time,
        args.weight_vote,
        args.rep_asa,
        args.algod_url,
    )
