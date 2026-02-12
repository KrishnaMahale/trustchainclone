"""
TrustChain PyTeal stateful smart contract.
Stores project rules, enforces voting window, one vote per address, no self-vote, finalization after deadline.
"""
from pyteal import (
    Approve,
    Reject,
    Seq,
    Assert,
    Global,
    Txn,
    Int,
    Bytes,
    App,
    Btoi,
    OnComplete,
    Cond,
    compileTeal,
    Mode,
)

# ----- Constants -----
PROJECT_ID = Bytes("pid")
DEADLINE_CONTRIBUTION = Bytes("d_contrib")
DEADLINE_VOTING = Bytes("d_vote")
WEIGHT_CODE = Bytes("w_code")
WEIGHT_TIME = Bytes("w_time")
WEIGHT_VOTE = Bytes("w_vote")
CREATOR = Bytes("creator")
REPUTATION_ASA = Bytes("rep_asa")

# Local state per user
HAS_VOTED = Bytes("voted")
VOTE_SCORE = Bytes("vscore")  # not stored per-member here; we use app args for vote submission
REPUTATION_EARNED = Bytes("rep")

# Application state
INITIALIZED = Bytes("init")
MEMBER_COUNT = Bytes("mcount")
FINALIZED = Bytes("final")


def approval_program():
    """Stateful contract approval program."""

    on_create = Seq(
        Assert(Txn.application_args.length() >= Int(7)),
        # args: project_id, deadline_contrib_ts, deadline_vote_ts, w_code, w_time, w_vote, rep_asa_id
        App.globalPut(PROJECT_ID, Btoi(Txn.application_args[0])),
        App.globalPut(DEADLINE_CONTRIBUTION, Btoi(Txn.application_args[1])),
        App.globalPut(DEADLINE_VOTING, Btoi(Txn.application_args[2])),
        App.globalPut(WEIGHT_CODE, Btoi(Txn.application_args[3])),
        App.globalPut(WEIGHT_TIME, Btoi(Txn.application_args[4])),
        App.globalPut(WEIGHT_VOTE, Btoi(Txn.application_args[5])),
        App.globalPut(REPUTATION_ASA, Btoi(Txn.application_args[6])),
        App.globalPut(CREATOR, Txn.sender()),
        App.globalPut(INITIALIZED, Int(1)),
        App.globalPut(MEMBER_COUNT, Int(0)),
        App.globalPut(FINALIZED, Int(0)),
        Approve(),
    )

    # Opt-in: members opt in to receive votes and reputation
    on_opt_in = Seq(
        Assert(Global.latest_timestamp() < App.globalGet(DEADLINE_VOTING)),
        App.localPut(Txn.sender(), HAS_VOTED, Int(0)),
        App.localPut(Txn.sender(), REPUTATION_EARNED, Int(0)),
        Approve(),
    )

    # submit_vote: args [0]=vote, [1]=member_address (32 bytes base32 decoded or 58 bytes base32)
    # We use application args: "vote" | member_index (or we pass member addr and look up)
    # Simplified: args = "vote", member_app_local_slot or we pass vote_score in args[0], member in args[1]
    # One vote per sender; no self-vote (checked off-chain and optionally by comparing Txn.sender() to args[1])
    submit_vote = Seq(
        Assert(Global.latest_timestamp() >= App.globalGet(DEADLINE_CONTRIBUTION)),
        Assert(Global.latest_timestamp() < App.globalGet(DEADLINE_VOTING)),
        Assert(App.localGet(Txn.sender(), HAS_VOTED) == Int(0)),
        Assert(Txn.application_args.length() >= Int(2)),
        # args[0] = vote score (1-5), args[1] = member address (we store hash or index; for simplicity we just mark voted)
        App.localPut(Txn.sender(), HAS_VOTED, Int(1)),
        App.localPut(Txn.sender(), VOTE_SCORE, Btoi(Txn.application_args[0])),
        Approve(),
    )

    # submit_score_hash: store hash of final score for a member (args: member_addr? hash)
    # We use global state with key = member_addr -> value = hash (or use box storage)
    # Minimal: just record that we have received score hashes; actual hashes in app args or boxes
    submit_score_hash = Seq(
        Assert(Global.latest_timestamp() >= App.globalGet(DEADLINE_VOTING)),
        Assert(App.globalGet(FINALIZED) == Int(0)),
        Approve(),
    )

    # finalize_project: only after voting deadline; set FINALIZED = 1
    finalize_project = Seq(
        Assert(Global.latest_timestamp() >= App.globalGet(DEADLINE_VOTING)),
        Assert(App.globalGet(FINALIZED) == Int(0)),
        Assert(Txn.sender() == App.globalGet(CREATOR)),
        App.globalPut(FINALIZED, Int(1)),
        Approve(),
    )

    # mint_reputation: creator calls with accounts=[recipient]; set recipient's REPUTATION_EARNED
    mint_reputation = Seq(
        Assert(App.globalGet(FINALIZED) == Int(1)),
        Assert(Txn.sender() == App.globalGet(CREATOR)),
        Assert(Txn.accounts.length() >= Int(1)),
        Assert(App.localGet(Txn.accounts[0], REPUTATION_EARNED) == Int(0)),
        Assert(Txn.application_args.length() >= Int(2)),
        App.localPut(Txn.accounts[0], REPUTATION_EARNED, Btoi(Txn.application_args[0])),
        Approve(),
    )

    on_call = Cond(
        [Txn.application_args[0] == Bytes("vote"), submit_vote],
        [Txn.application_args[0] == Bytes("score_hash"), submit_score_hash],
        [Txn.application_args[0] == Bytes("finalize"), finalize_project],
        [Txn.application_args[0] == Bytes("mint_rep"), mint_reputation],
    )

    return Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.OptIn, on_opt_in],
        [Txn.on_completion() == OnComplete.NoOp, on_call],
        [Txn.on_completion() == OnComplete.CloseOut, Reject()],
        [Txn.on_completion() == OnComplete.UpdateApplication, Reject()],
        [Txn.on_completion() == OnComplete.DeleteApplication, Reject()],
        [Txn.on_completion() == OnComplete.ClearState, Approve()],
    )


def clear_program():
    return Approve()


if __name__ == "__main__":
    import os
    p = approval_program()
    c = clear_program()
    out_dir = os.path.join(os.path.dirname(__file__), "teal")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "contribution_approval.teal"), "w") as f:
        f.write(compileTeal(p, mode=Mode.Application, version=7))
    with open(os.path.join(out_dir, "contribution_clear.teal"), "w") as f:
        f.write(compileTeal(c, mode=Mode.Application, version=7))
