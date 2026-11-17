"""Real backing-store scope experiments. Test-only namespaces are cleaned on success/failure."""

import os
from uuid import uuid4

import httpx
import pytest

SCOPE = {"organization_id": "a", "repository_id": "r", "snapshot_id": "s", "generation_id": "g"}


@pytest.mark.skipif(not os.getenv("CODEATLAS_TEST_QDRANT"), reason="Real Qdrant URL not configured")
def test_qdrant_all_scope_filters_before_ranking():
    collection = "phase0_" + uuid4().hex
    with httpx.Client(base_url=os.environ["CODEATLAS_TEST_QDRANT"], timeout=20) as client:
        client.put(
            f"/collections/{collection}", json={"vectors": {"size": 2, "distance": "Cosine"}}
        ).raise_for_status()
        try:
            variants = [SCOPE] + [{**SCOPE, key: "denied"} for key in SCOPE]
            client.put(
                f"/collections/{collection}/points?wait=true",
                json={
                    "points": [
                        {"id": i + 1, "vector": [1.0, 0.0], "payload": value}
                        for i, value in enumerate(variants)
                    ]
                },
            ).raise_for_status()
            for key in SCOPE:
                client.put(
                    f"/collections/{collection}/index?wait=true",
                    json={"field_name": key, "field_schema": "keyword"},
                ).raise_for_status()
            response = client.post(
                f"/collections/{collection}/points/search",
                json={
                    "vector": [1.0, 0.0],
                    "limit": 10,
                    "with_payload": True,
                    "filter": {
                        "must": [{"key": k, "match": {"value": v}} for k, v in SCOPE.items()]
                    },
                },
            )
            response.raise_for_status()
            assert [row["id"] for row in response.json()["result"]] == [1]
        finally:
            client.delete(f"/collections/{collection}").raise_for_status()


@pytest.mark.skipif(not os.getenv("CODEATLAS_TEST_NEO4J"), reason="Real Neo4j URI not configured")
def test_neo4j_scopes_every_node_and_edge():
    neo4j = pytest.importorskip("neo4j")
    run_id = uuid4().hex
    # Deliberately malformed cross-generation nodes/edges test traversal containment.
    with neo4j.GraphDatabase.driver(
        os.environ["CODEATLAS_TEST_NEO4J"],
        auth=("neo4j", "local-spike-password"),
        connection_timeout=5,
        max_transaction_retry_time=5,
    ) as driver:
        with driver.session() as session:
            session.run(
                "CREATE (a:Phase0) SET a=$props", props={**SCOPE, "run": run_id, "name": "seed"}
            ).consume()
            try:
                variants = [(SCOPE, SCOPE)]
                variants += [({**SCOPE, key: "denied"}, SCOPE) for key in SCOPE]
                variants += [(SCOPE, {**SCOPE, key: "denied"}) for key in SCOPE]
                for index, (node_scope, edge_scope) in enumerate(variants):
                    session.run(
                        "MATCH (a:Phase0 {run:$run, name:'seed'}) "
                        "CREATE (a)-[e:LINK]->(b:Phase0) SET b=$node, e=$edge",
                        run=run_id,
                        node={**node_scope, "run": run_id, "name": str(index)},
                        edge=edge_scope,
                    ).consume()
                result = session.run(
                    "MATCH p=(a:Phase0 {run:$run, name:'seed'})-[:LINK*1..2]->(b:Phase0) "
                    "WHERE all(n IN nodes(p) WHERE n.run=$run "
                    "AND all(k IN keys($scope) WHERE n[k]=$scope[k])) "
                    "AND all(e IN relationships(p) WHERE "
                    "all(k IN keys($scope) WHERE e[k]=$scope[k])) "
                    "RETURN b.name AS name",
                    run=run_id,
                    scope=SCOPE,
                )
                assert [row["name"] for row in result] == ["0"]
            finally:
                session.run("MATCH (n:Phase0 {run:$run}) DETACH DELETE n", run=run_id).consume()
