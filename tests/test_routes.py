"""The routes: one tree, claimed for as long as the process runs.

What is worth testing here is not that the routes return JSON. It is the three things the
process model claims and nothing before it could: that a read is served while a write is in
flight, that a second write is refused rather than queued, and that a failure says which of
the three kinds it was. The rest is projection, which is tested where a shape would
otherwise be silently wrong -- a token that spells no character, a source that is an id --
and the page, where the order of the route list is the whole of what it rests on.
"""

from __future__ import annotations

import math
import threading

import pytest
from starlette.testclient import TestClient

from tokenloom.core import Generation, Store, StoreError
from tokenloom.core import reads as R
from tokenloom.surface.app import PAGE, Backend, Writer, build_app
from toy import FRAG_HI, FRAG_LO, MODEL, USER, ToyAdapter, ToyVocabulary, drew


def build(path):
    """Two roots, a fork with a deleted arm, and a ranking with one row unrealised.

        1  'The'         live
        2   ' sky'       live, ranked: ' is' realised, ' red' and ' blue' not
        3    ' is'       live
        4     ' blue'    live
        5    ' red'      deleted
        6  ' grey'       live, a second root
    """
    with Store.initialise(path, vocabulary="toy") as store:
        store.create(None, "The sky", vocabulary=ToyVocabulary(), actor=USER)
        store.generate(
            2, {"length": 1},
            adapter=ToyAdapter([drew((102, [(102, -0.1), (104, -0.9), (103, -2.0)]))]),
            actor=USER,
        )
        store.create(3, " blue", vocabulary=ToyVocabulary(), actor=USER)
        store.create(2, " red", vocabulary=ToyVocabulary(), actor=USER)
        store.create(None, " grey", vocabulary=ToyVocabulary(), actor=USER)
        store.delete(5, actor=USER)
    return path


@pytest.fixture
def adapter():
    return ToyAdapter([])


@pytest.fixture
def writer(tmp_path):
    held = Writer(build(tmp_path / "t"))
    yield held
    held.close()


@pytest.fixture
def client(writer, adapter):
    return TestClient(build_app(writer, Backend(lambda: adapter)))


# ---- the claim -----------------------------------------------------------------------


def test_a_tree_another_process_holds_cannot_be_served(writer, tmp_path):
    """Reported by whoever asked for it, and naming the tree, rather than as a server that
    comes up and never resolves."""
    with pytest.raises(StoreError, match=str(tmp_path / "t")):
        Writer(tmp_path / "t")


def test_closing_the_writer_releases_the_claim(tmp_path):
    first = Writer(build(tmp_path / "t"))
    first.close()
    Writer(tmp_path / "t").close()  # raises if the claim outlived its holder


def test_a_read_connection_cannot_write(writer):
    """`query_only`, so a read handler that reached for the store could not become a second
    writer by accident."""
    conn = writer.reader()
    try:
        with pytest.raises(Exception, match="readonly"):
            conn.execute("UPDATE nodes SET deleted = 1 WHERE id = 1")
    finally:
        conn.close()


# ---- a read while a write is in flight -----------------------------------------------


def test_reading_goes_on_while_a_write_is_in_flight_and_a_second_write_does_not(
    writer, client
):
    """The property the whole process model is for.

    The blocked generate is inside `adapter.generate`, which is where a real one spends its
    seconds and where `docs/CORE.md` is explicit that no transaction is open. So the read
    has to be served, and the second write has to be told no rather than queued.
    """
    inside, go = threading.Event(), threading.Event()

    def block(ids, params):
        inside.set()
        go.wait(5)
        return drew((103, None))

    slow = ToyAdapter([block])
    done = []
    thread = threading.Thread(
        target=lambda: done.append(
            writer.act(lambda store: store.generate(4, {"length": 1},
                                                    adapter=slow, actor=USER))
        )
    )
    thread.start()
    assert inside.wait(5), "the generate never reached the adapter"
    try:
        served = client.get("/path/4")
        assert served.status_code == 200

        in_flight = client.get("/acts", params={"in_flight": "1"}).json()
        assert [a["terminator"] for a in in_flight["acts"]] == [None]

        refused = client.post("/delete", json={"node": 4})
        assert refused.status_code == 409
        assert refused.json()["error"] == "busy"
    finally:
        go.set()
        thread.join(5)
    assert done and done[0][1].terminator == "limit"
    assert client.get("/acts", params={"in_flight": "1"}).json()["acts"] == []


# ---- the three reads ------------------------------------------------------------------


def test_the_tree_read_names_its_roots_and_its_vocabulary(client):
    body = client.get("/tree").json()
    assert body["vocabulary"] == "toy"
    assert [r["id"] for r in body["roots"]] == [1, 6]
    assert body["counts"]["nodes"] == 6


def test_a_root_is_named_by_what_it_opens_with_and_by_what_is_live(client):
    """A label is drawn from the live tree, so deleting an arm lengthens one and undeleting
    it cuts it back. The text alone cannot say which stop it was, which is what `forked` is
    for: here it turns over without the label ever being wrong about the characters."""
    before = {r["id"]: r for r in client.get("/tree").json()["roots"]}
    assert (before[1]["label"], before[1]["forked"]) == ("The sky is blue", False)
    assert (before[6]["label"], before[6]["forked"]) == (" grey", False)

    assert client.post("/undelete", json={"node": 5}).status_code == 201

    after = {r["id"]: r for r in client.get("/tree").json()["roots"]}
    assert (after[1]["label"], after[1]["forked"]) == ("The sky", True)
    assert after[6] == before[6]


def test_a_path_runs_to_the_leaf_the_rule_chooses(client):
    body = client.get("/path/2").json()
    assert body["leaf"] == 4
    assert "".join(cell["text"] for cell in body["segments"]) == "The sky is blue"
    assert [n["id"] for cell in body["segments"] for n in cell["nodes"]] == [1, 2, 3, 4]


def test_the_ancestry_alone_is_what_rule_none_asks_for(client):
    body = client.get("/path/2", params={"rule": "none"}).json()
    assert body["leaf"] == 2
    assert "".join(cell["text"] for cell in body["segments"]) == "The sky"


def test_a_rule_this_server_does_not_have_is_a_bad_request(client):
    answer = client.get("/path/2", params={"rule": "shortest"})
    assert answer.status_code == 400
    assert "longest" in answer.json()["message"]


def test_a_path_carries_what_is_derived_at_each_node(client):
    """Liveness, the logprob off the ranking above, and the fork -- none of which is a
    column on a node, and all of which a client would otherwise ask for per node."""
    marks = {n["id"]: n for cell in client.get("/path/2").json()["segments"]
             for n in cell["nodes"]}
    assert marks[3]["logprob"] == pytest.approx(-0.1)
    assert marks[1]["logprob"] is None
    assert all(n["live"] for n in marks.values())
    # node 5 is deleted, so node 2 does not part anywhere a reader can follow
    assert [i for i, n in marks.items() if n["fork"]] == []

    client.post("/undelete", json={"node": 5})
    after = {n["id"]: n for cell in client.get("/path/2").json()["segments"]
             for n in cell["nodes"]}
    assert [i for i, n in after.items() if n["fork"]] == [3]


def test_the_hidden_toggle_carries_a_path_past_what_was_set_aside(client):
    """A tail set aside truncates the path, which is what a reader pruning one wants. What
    the toggle does is bring it back into view without bringing it back into the tree, so
    there is somewhere to undo it from."""
    assert client.post("/delete", json={"node": 4}).status_code == 201

    plain = client.get("/path/3").json()
    assert [n["id"] for cell in plain["segments"] for n in cell["nodes"]] == [1, 2, 3]
    assert plain["hidden"] is False

    shown = client.get("/path/3", params={"hidden": 1}).json()
    marks = [n for cell in shown["segments"] for n in cell["nodes"]]
    assert [n["id"] for n in marks] == [1, 2, 3, 4]
    assert [n["live"] for n in marks] == [True, True, True, False]
    assert marks[-1]["deleted"] is True, "revealing it is not restoring it"
    assert shown["hidden"] is True
    assert shown["leaf"] == 4


def test_the_toggle_is_off_by_being_absent_and_by_being_denied(client):
    """A bare `?hidden` is the reader meaning it; `hidden=0` is a client saying so."""
    client.post("/delete", json={"node": 4})
    assert client.get("/path/3").json()["leaf"] == 3
    assert client.get("/path/3", params={"hidden": 0}).json()["leaf"] == 3
    assert client.get("/path/3?hidden").json()["leaf"] == 4


def test_a_path_carries_no_overlay_until_one_is_asked_for(client):
    """The floor case is a text reader, so it does not pay for what it does not draw. An
    absent key and an empty list are different answers: *nobody asked*, and *nothing ranked
    this position* -- and a client that read them the same would draw a hole wherever the
    read had simply not been told to compute one."""
    plain = [n for cell in client.get("/path/2").json()["segments"] for n in cell["nodes"]]
    assert all("among" not in n for n in plain)

    body = client.get("/path/2", params={"overlays": 1}).json()
    assert body["overlays"] is True
    marks = {n["id"]: n for cell in body["segments"] for n in cell["nodes"]}
    assert all("among" in n for n in marks.values())
    assert marks[1]["among"] == [], "a root stood in no ranking"
    assert marks[2]["among"] == [], "node 1 ranked nothing, so node 2 stood in nothing"


def test_an_overlay_is_what_the_ranking_above_says_about_the_position(client):
    """Node 2 carries the only ranking in this tree, so node 3 is the one node that stood
    in one. What it reports has to agree with the rows the ranking read hands back, which
    is the same answer at a different width."""
    marks = {n["id"]: n for cell in
             client.get("/path/2", params={"overlays": 1}).json()["segments"]
             for n in cell["nodes"]}
    (stood,) = marks[3]["among"]
    rows = client.get("/ranking/2").json()["rows"]

    assert stood["rows"] == len(rows)
    assert stood["top"] == max(row["logprob"] for row in rows)
    assert stood["second"] == sorted((row["logprob"] for row in rows), reverse=True)[1]
    assert stood["mass"] == pytest.approx(sum(math.exp(row["logprob"]) for row in rows))
    # The flag: what node 3 paid to be where it is, which here is nothing.
    assert marks[3]["logprob"] == stood["top"]
    assert stood["source"] == marks[3]["source"]


def test_a_ranking_says_which_rows_have_been_realised(client):
    body = client.get("/ranking/2").json()
    rows = {row["token"]: row for row in body["rows"]}
    assert rows[102]["child"] == 3
    assert rows[104]["child"] is None and rows[103]["child"] is None
    assert [row["token"] for row in body["rows"]] == [102, 104, 103]  # descending logprob
    assert body["sources"][str(rows[102]["source"])] == str(MODEL)


def test_a_node_with_no_ranking_is_not_the_same_as_no_node(client):
    assert client.get("/ranking/4").json()["rows"] == []
    assert client.get("/ranking/9999").status_code == 404


def test_a_line_hangs_where_it_parts_and_not_where_it_is_deep(client):
    """The column is where paths part. Node 5 is deleted, so node 2 offers one line; undo
    that and it offers two, both at the split. A line that parts later sits later."""
    def lines(at):
        body = client.get(f"/branches/{at}", params={"budget": "40"}).json()
        return [("".join(c["text"] for c in b["segments"]), b["parts_at"], b["branches"])
                for b in body["branches"]]

    # a preview line's nodes are ids: a record each would repeat what the run already says
    assert [c["nodes"] for c in
            client.get("/branches/2", params={"budget": "40"}).json()["branches"][0]["segments"]
            ] == [[3], [4]]

    assert [(text, at) for text, at, _ in lines(2)] == [(" is blue", 0)]

    client.post("/undelete", json={"node": 5})
    assert [(text, at) for text, at, _ in lines(2)] == [(" is blue", 0), (" red", 0)]

    client.post("/create", json={"at": 3, "text": " grey"})
    first, second = lines(2)
    assert (first[0], first[1]) == (" is blue", 0)
    assert [(("".join(c["text"] for c in b["segments"])), b["parts_at"])
            for b in first[2]] == [(" grey", len(" is"))]
    assert (second[0], second[1]) == (" red", 0)


def test_a_branch_read_without_a_budget_is_a_bad_request(client):
    answer = client.get("/branches/1")
    assert answer.status_code == 400
    assert answer.json()["error"] == "bad_request"


# ---- what does not decode -------------------------------------------------------------


def test_a_token_that_spells_no_character_crosses_marked(client, writer):
    """A segment is several nodes across a multi-token character, and a path that ends
    inside one has no string form. Both have to survive the projection."""
    def drew_at(at, token):
        writer.act(lambda store: store.generate(
            at, {"length": 1}, adapter=ToyAdapter([drew((token, None))]), actor=USER,
        ))
        return writer.act(lambda store: R.children(store.conn, at)[0].id)

    high = drew_at(4, FRAG_HI)
    ends_inside = client.get(f"/path/{high}", params={"rule": "none"}).json()
    assert ends_inside["segments"][-1] == {
        "text": "\ufffd", "decodes": False, "nodes": [ends_inside["segments"][-1]["nodes"][0]]
    }
    assert [n["id"] for n in ends_inside["segments"][-1]["nodes"]] == [high]

    low = drew_at(high, FRAG_LO)
    whole = client.get(f"/path/{low}").json()["segments"][-1]
    assert whole["text"] == "\u00e9" and whole["decodes"] is True
    assert [n["id"] for n in whole["nodes"]] == [high, low]


# ---- the five acts --------------------------------------------------------------------


def test_each_act_answers_with_what_it_produced(client):
    made = client.post("/create", json={"at": 4, "text": " grey"})
    assert made.status_code == 201
    body = made.json()
    assert body["op"] == "create" and body["origin"] == 4
    assert [n["token"] for n in body["nodes"]] == [105]
    assert body["tip"] == body["nodes"][-1]["id"]


def test_a_create_may_attribute_its_text_to_someone_other_than_the_actor(client):
    body = client.post(
        "/create", json={"at": 4, "text": " grey", "attribute": "model:elsewhere"}
    ).json()
    made = body["nodes"][0]["source"]
    assert client.get("/tree").json()["sources"][str(made)] == "model:elsewhere"
    assert made != body["actor"]


def test_realise_takes_the_edge_the_ranking_named(client):
    row = next(r for r in client.get("/ranking/2").json()["rows"] if r["child"] is None)
    body = client.post(
        "/realise", json={"at": 2, "rank": row["rank"], "source": str(MODEL)}
    ).json()
    assert body["op"] == "realise" and body["rank"] == row["rank"]
    assert [n["token"] for n in body["nodes"]] == [row["token"]]
    assert client.get("/ranking/2").json()["rows"][1]["child"] == body["tip"]


def test_delete_and_undelete_answer_with_the_liveness_they_changed(client):
    gone = client.post("/delete", json={"node": 4}).json()
    assert gone["op"] == "delete" and gone["live"] is False and gone["nodes"] == []
    back = client.post("/undelete", json={"node": 4}).json()
    assert back["op"] == "undelete" and back["live"] is True


def test_a_generate_answers_with_its_nodes_and_its_terminator(client, adapter):
    adapter.answers.append(drew((104, [(104, -0.3)])))
    body = client.post("/generate", json={"at": 4, "params": {"length": 1}}).json()
    assert body["op"] == "generate" and body["terminator"] == "limit"
    assert body["params"] == {"length": 1}
    assert [n["token"] for n in body["nodes"]] == [104]


# ---- and how each way of failing says which it was ------------------------------------


def test_a_rejection_is_a_bad_request_and_names_no_act(client):
    """The core declined before writing anything, so there is nothing in the record to
    point at."""
    answer = client.post("/create", json={"at": 5, "text": " blue"})
    assert answer.status_code == 400
    assert answer.json()["error"] == "rejected"
    assert "act" not in answer.json()
    assert client.get("/acts").json()["acts"][0]["op"] != "create"


def test_a_refusal_carries_the_act_it_stands_as(client, adapter):
    """The adapter declined, and `docs/SURFACE.md` has the surface naming that act."""
    adapter.answers.append(Generation("refused", (), reason="not from here"))
    answer = client.post("/generate", json={"at": 4, "params": {"length": 1}})
    assert answer.status_code == 422
    body = answer.json()
    assert body["error"] == "refused" and body["message"] == "not from here"
    assert body["act"]["terminator"] == "refused"
    assert client.get("/acts").json()["acts"][0]["id"] == body["act"]["id"]


def test_a_failure_is_in_the_record_even_though_the_answer_cannot_name_it(client, adapter):
    adapter.answers.append(RuntimeError("the backend fell over"))
    answer = client.post("/generate", json={"at": 4, "params": {"length": 1}})
    assert answer.status_code == 502
    assert answer.json()["error"] == "failed"
    assert client.get("/acts").json()["acts"][0]["terminator"] == "failed"


def test_a_generate_the_core_rejects_never_reaches_the_backend(client, adapter):
    """`length` is checked before the act is written, so this is a rejection and not a
    failure -- and the distinction is the one the status codes carry."""
    answer = client.post("/generate", json={"at": 4, "params": {"length": 0}})
    assert answer.status_code == 400
    assert answer.json()["error"] == "rejected"
    assert adapter.answers == []


def test_a_node_that_is_not_there_is_not_found(client):
    for route in ("/path/9999", "/ranking/9999", "/branches/9999?budget=40"):
        answer = client.get(route)
        assert answer.status_code == 404, route
        assert answer.json()["error"] == "not_found"


# ---- the backend, built on first need -------------------------------------------------


def test_a_tree_is_read_and_three_acts_are_made_with_no_backend_at_all(writer):
    def missing():
        raise OSError("connection refused")

    client = TestClient(build_app(writer, Backend(missing)))
    assert client.get("/tree").status_code == 200
    assert client.get("/path/2").status_code == 200
    assert client.post("/delete", json={"node": 4}).status_code == 201
    assert client.post("/undelete", json={"node": 4}).status_code == 201
    assert client.post(
        "/realise", json={"at": 2, "rank": 1, "source": str(MODEL)}
    ).status_code == 201


def test_what_needs_the_backend_says_so_where_it_is_wanted(writer):
    def missing():
        raise OSError("connection refused")

    client = TestClient(build_app(writer, Backend(missing)))
    for answer in (
        client.post("/create", json={"at": 4, "text": " grey"}),
        client.post("/generate", json={"at": 4, "params": {"length": 1}}),
        client.get("/evaluable", params={"node": "4"}),
    ):
        assert answer.status_code == 503
        assert answer.json()["error"] == "backend"
        assert "connection refused" in answer.json()["message"]


def test_the_backend_is_built_once_and_kept(writer, adapter):
    built = []

    def build_one():
        built.append(1)
        return adapter

    client = TestClient(build_app(writer, Backend(build_one)))
    client.get("/evaluable", params={"node": "4"})
    client.get("/evaluable", params={"node": "2"})
    assert built == [1]


def test_the_path_predicate_is_asked_of_the_backend_and_writes_nothing(client, writer):
    before = client.get("/acts").json()["acts"]
    assert client.get("/evaluable", params={"node": "4"}).json() == {
        "node": 4, "evaluable": True
    }
    assert client.get("/evaluable").json() == {"node": None, "evaluable": True}
    assert client.get("/acts").json()["acts"] == before


# ---- and the page, served from the same process ---------------------------------------


def test_the_page_is_at_the_root_and_shadows_none_of_the_routes(client):
    """The mount is last, so a named route is reached and the page is what is left over.

    Were it first, every route below would answer 404 from the file system instead, which is
    a failure that looks like a missing tree rather than a misordered list.
    """
    page = client.get("/")
    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    assert client.get("/tree").json()["vocabulary"] == "toy"

    # What the page pulls for itself comes off the same mount, so a file left out of the
    # package is a 404 here rather than a page that loads and does nothing. Every file that
    # ships is checked rather than a list of them, which would go stale as the page grows.
    kinds = {".css": "text/css", ".js": "text/javascript"}
    assets = sorted((PAGE / "assets").iterdir())
    assert assets, "the page has no assets, which is not a state it has ever been in"
    for asset in assets:
        served = client.get(f"/assets/{asset.name}")
        assert served.status_code == 200, asset.name
        assert served.headers["content-type"].startswith(kinds[asset.suffix]), asset.name


def test_a_path_that_is_neither_a_route_nor_a_file_is_not_the_page(client):
    """`html=True` serves the index for a directory and not for anything else, so a client
    asking for a route this server does not have is told so rather than handed the page."""
    assert client.get("/nope").status_code == 404
