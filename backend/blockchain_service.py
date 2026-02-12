"""
Algorand blockchain service: deploy app, submit vote, finalize, mint reputation.
Uses Algorand SDK and optional AlgoKit for deployment.
"""
import base64
import hashlib
from typing import List, Optional, Tuple
from datetime import datetime
from algosdk import account, encoding, logic
from algosdk.v2client import algod
from algosdk import transaction
from algosdk.abi import Method, Contract
from config import get_settings

settings = get_settings()


def get_algod_client() -> algod.AlgodClient:
    return algod.AlgodClient(settings.ALGOD_TOKEN or "", settings.ALGOD_URL)


def _get_sender_private_key(mnemonic: str) -> str:
    """Derive private key from mnemonic (creator/deployer)."""
    from algosdk import mnemonic as mn
    return mn.to_private_key(mnemonic)


def create_project_contract(
    creator_mnemonic: str,
    project_id: int,
    deadline_contribution_ts: int,
    deadline_voting_ts: int,
    weight_code_int: int,
    weight_time_int: int,
    weight_vote_int: int,
    reputation_asa_id: int,
    approval_teal: str,
    clear_teal: str,
) -> Tuple[int, str]:
    """
    Deploy stateful application. Returns (app_id, app_address).
    Weights passed as integers e.g. 40, 30, 30 for 0.4, 0.3, 0.3.
    """
    client = get_algod_client()
    private_key = _get_sender_private_key(creator_mnemonic)
    sender = account.address_from_private_key(private_key)

    # Compile approval and clear
    approval_result = client.compile(approval_teal)
    clear_result = client.compile(clear_teal)
    approval_binary = base64.b64decode(approval_result["result"])
    clear_binary = base64.b64decode(clear_result["result"])

    params = client.suggested_params()
    # Create app with args: project_id, d_contrib, d_vote, w_code, w_time, w_vote, rep_asa
    app_args = [
        project_id.to_bytes(8, "big"),
        deadline_contribution_ts.to_bytes(8, "big"),
        deadline_voting_ts.to_bytes(8, "big"),
        weight_code_int.to_bytes(8, "big"),
        weight_time_int.to_bytes(8, "big"),
        weight_vote_int.to_bytes(8, "big"),
        reputation_asa_id.to_bytes(8, "big"),
    ]
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
    return app_id, app_address


def opt_in_member(member_private_key: str, app_id: int) -> str:
    """Opt-in a member to the app. Member must sign (use member's key from wallet)."""
    client = get_algod_client()
    sender = account.address_from_private_key(member_private_key)
    params = client.suggested_params()
    txn = transaction.ApplicationOptInTxn(sender, params, app_id)
    signed = txn.sign(member_private_key)
    txid = client.send_transaction(signed)
    transaction.wait_for_confirmation(client, txid, 4)
    return txid


def submit_vote_sender_signed(
    app_id: int,
    voter_private_key: str,
    vote_score: int,
    member_address_bytes: Optional[bytes] = None,
) -> str:
    """Submit vote (NoOp) with args: 'vote', score. Voter must have opted in."""
    client = get_algod_client()
    sender = account.address_from_private_key(voter_private_key)
    params = client.suggested_params()
    txn = transaction.ApplicationNoOpTxn(
        sender,
        params,
        app_id,
        [b"vote", vote_score.to_bytes(8, "big")],
    )
    signed = txn.sign(voter_private_key)
    txid = client.send_transaction(signed)
    transaction.wait_for_confirmation(client, txid, 4)
    return txid


def submit_score_hash_txn(
    creator_mnemonic: str,
    app_id: int,
    score_hash: str,
) -> str:
    """Submit score hash (NoOp). Creator or backend account."""
    client = get_algod_client()
    private_key = _get_sender_private_key(creator_mnemonic)
    sender = account.address_from_private_key(private_key)
    params = client.suggested_params()
    txn = transaction.ApplicationNoOpTxn(
        sender,
        params,
        app_id,
        [b"score_hash", score_hash.encode()],
    )
    signed = txn.sign(private_key)
    txid = client.send_transaction(signed)
    transaction.wait_for_confirmation(client, txid, 4)
    return txid


def finalize_project(creator_mnemonic: str, app_id: int) -> str:
    """Call finalize on contract. Only creator, after voting deadline."""
    client = get_algod_client()
    private_key = _get_sender_private_key(creator_mnemonic)
    sender = account.address_from_private_key(private_key)
    params = client.suggested_params()
    txn = transaction.ApplicationNoOpTxn(
        sender,
        params,
        app_id,
        [b"finalize"],
    )
    signed = txn.sign(private_key)
    txid = client.send_transaction(signed)
    transaction.wait_for_confirmation(client, txid, 4)
    return txid


def mint_reputation_txn(
    creator_mnemonic: str,
    app_id: int,
    asa_id: int,
    recipient: str,
    amount: int,
) -> str:
    """
    Transfer reputation ASA from creator to recipient.
    Contract records REPUTATION_EARNED in local state via 'mint_rep' call;
    actual ASA transfer is from creator (who holds the ASA) to recipient.
    """
    client = get_algod_client()
    private_key = _get_sender_private_key(creator_mnemonic)
    sender = account.address_from_private_key(private_key)
    params = client.suggested_params()
    # 1) NoOp mint_rep to record in contract
    noop = transaction.ApplicationNoOpTxn(
        sender,
        params,
        app_id,
        [b"mint_rep", amount.to_bytes(8, "big")],
        [recipient],
    )
    # 2) Asset transfer from sender to recipient
    xfer = transaction.AssetTransferTxn(sender, params, recipient, amount, asa_id)
    gid = transaction.calculate_group_id([noop, xfer])
    noop.group = gid
    xfer.group = gid
    signed_noop = noop.sign(private_key)
    signed_xfer = xfer.sign(private_key)
    txid = client.send_transactions([signed_noop, signed_xfer])
    transaction.wait_for_confirmation(client, txid, 4)
    return txid


def hash_score(code_score: float, time_score: float, peer_score: float, final_score: float) -> str:
    """SHA256 hash of score tuple for on-chain verification."""
    payload = f"{code_score:.2f}|{time_score:.2f}|{peer_score:.2f}|{final_score:.2f}"
    return hashlib.sha256(payload.encode()).hexdigest()


def read_app_global_state(app_id: int) -> dict:
    """Read global state of the app (for verification)."""
    client = get_algod_client()
    try:
        info = client.application_info(app_id)
    except Exception:
        return {}
    state = {}
    params = info.get("params", {})
    for s in params.get("global-state", []):
        key = base64.b64decode(s["key"])
        state[key.decode("utf-8", errors="replace")] = s["value"]
    return state
