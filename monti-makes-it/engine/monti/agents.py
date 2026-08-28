"""Per-client agents, scoped at the data layer (Appendix B, client agent contract).

Every customer gets an agent. The whole difficulty is in one sentence of the
contract:

    "A prompt naming another client returns nothing because the query cannot
     reach it — not because the agent declines."

That distinction is the entire design. An agent that refuses because its
instructions told it to is one clever prompt away from not refusing. So the
scope is not instruction text: it is a `customer_id` captured when the agent is
constructed and welded into the WHERE clause of every query it can run. There is
no method on `ScopedData` that accepts a customer id from the caller, which
means there is no argument an injected prompt can supply to change it. Asking
this agent about another customer does not produce a refusal — it produces an
empty result, because the row was never in the query's reach.

The second rule is that an agent proposes and never publishes. It cannot set a
price, change an order state, clear a review, alter a registration, or write to
any customer record — including its own. Everything it produces lands in
`agent_proposals` and goes through the same admin publish step as any other
input. That is enforced the same way: this module has no write method other than
`propose`.
"""
from .db import execute, query

TEMPLATE_VERSION = "cli-template-1.0"


class ScopeViolation(Exception):
    """Raised when something tries to widen an agent's scope.

    Reaching this is a bug in our own code, not an attack that got through: the
    query layer below cannot be pointed at another customer, so the only way
    here is a caller constructing a ScopedData for a customer the agent is not
    bound to.
    """


class ScopedData:
    """The only way a client agent touches the database.

    `customer_id` is set once in __init__ and read from `self` by every method.
    No method takes a customer parameter, so there is nothing for a prompt to
    pass. The agent's tool layer holds one of these and has no other database
    access.
    """

    def __init__(self, customer_id, agent_ref):
        if not customer_id:
            raise ScopeViolation("a client agent must be bound to a customer")
        self._customer_id = int(customer_id)
        self._agent_ref = agent_ref

    # -- reads, every one of them filtered on the bound customer --------------
    def customer(self):
        return query("SELECT * FROM customers WHERE id = ?", (self._customer_id,), one=True)

    def items(self):
        return query(
            "SELECT i.*, r.unit_price_cents, r.moq, r.lead_time_days "
            "FROM catalogue_registrations r JOIN catalog_items i ON i.id = r.item_id "
            "WHERE r.customer_id = ? AND r.active = 1", (self._customer_id,))

    def orders(self):
        return query("SELECT * FROM orders WHERE customer_id = ? ORDER BY created_at DESC",
                     (self._customer_id,))

    def quotes(self):
        return query("SELECT * FROM quotes WHERE customer_id = ? ORDER BY created_at DESC",
                     (self._customer_id,))

    def price_matrix(self):
        return query(
            "SELECT m.*, c.quantity_min, c.quantity_max, c.spec_tier, c.unit_price_cents "
            "FROM price_matrices m JOIN price_matrix_cells c ON c.matrix_id = m.id "
            "WHERE m.customer_id = ? AND m.published_at IS NOT NULL "
            "ORDER BY c.quantity_min, c.spec_tier", (self._customer_id,))

    def on_time_record(self):
        return query(
            "SELECT COUNT(*) AS shipped, "
            "       SUM(CASE WHEN delivered_at IS NOT NULL THEN 1 ELSE 0 END) AS delivered "
            "FROM orders WHERE customer_id = ? AND status IN ('SHIPPED','DELIVERED')",
            (self._customer_id,), one=True)

    def search_customers(self, name):
        """Look up a customer by name — within scope, which is one customer.

        This is the method a cross-client prompt injection would aim at, and it
        is why the check is a comparison against `self._customer_id` in SQL
        rather than a decision the agent makes. Asking for another company's
        name returns an empty list. The attempt is logged, because a client
        agent being asked about someone else is worth seeing even though it
        cannot succeed.
        """
        rows = query(
            "SELECT * FROM customers WHERE id = ? AND lower(company_name) LIKE ?",
            (self._customer_id, f"%{(name or '').lower()}%"))
        execute(
            "INSERT INTO agent_access_log (agent_ref, bound_customer_id, requested, refused) "
            "VALUES (?, ?, ?, ?)",
            (self._agent_ref, self._customer_id, f"customer search: {name!r}",
             0 if rows else 1))
        return rows

    # -- the only write ------------------------------------------------------
    def propose(self, kind, body):
        """File a proposal for an admin to accept or reject. Never a publish."""
        agent = query("SELECT * FROM client_agents WHERE customer_id = ?",
                      (self._customer_id,), one=True)
        if agent is None:
            raise ScopeViolation("no agent is provisioned for this customer")
        if agent["status"] != "ACTIVE":
            raise ScopeViolation(f"agent {agent['ref']} is {agent['status'].lower()}")
        return execute(
            "INSERT INTO agent_proposals (agent_id, customer_id, kind, body) "
            "VALUES (?, ?, ?, ?)", (agent["id"], self._customer_id, kind, body))


def agent_for(customer_id):
    """The scoped data layer for one customer's agent, or None if not provisioned."""
    agent = query("SELECT * FROM client_agents WHERE customer_id = ?", (customer_id,), one=True)
    if agent is None:
        return None
    return ScopedData(agent["customer_id"], agent["ref"])


def provision_agent(customer_id):
    """Creating a customer provisions their agent. No customer without an agent."""
    existing = query("SELECT * FROM client_agents WHERE customer_id = ?",
                     (customer_id,), one=True)
    if existing:
        return existing["id"]
    count = query("SELECT COUNT(*) AS c FROM client_agents", one=True)["c"]
    agent_id = execute(
        "INSERT INTO client_agents (ref, customer_id, template_version, scope_verified_at) "
        "VALUES (?, ?, ?, datetime('now'))",
        (f"CLI-{count + 1:02d}", customer_id, TEMPLATE_VERSION))
    return agent_id


def set_agent_status(customer_id, status, reason):
    """Lifecycle: suspend on pause, revoke on decline or close, reinstate on return.

    Every transition is stamped and reasoned, because "the agent stopped
    answering" with no record of why is indistinguishable from a bug.
    """
    if status not in ("ACTIVE", "SUSPENDED", "REVOKED"):
        raise ValueError(f"unknown agent status: {status!r}")
    execute(
        "UPDATE client_agents SET status = ?, status_changed_at = datetime('now'), "
        "status_reason = ? WHERE customer_id = ?", (status, reason, customer_id))


def sync_with_membership(customer_id, membership_status):
    """Keep the agent's state in step with the account's, in one place.

    Called wherever membership changes, so the lifecycle rule lives here rather
    than being re-derived at each of the several places a status can move.
    """
    mapping = {
        "MEMBER": ("ACTIVE", "account is a member"),
        "PAUSED": ("SUSPENDED", "account paused"),
        "DECLINED": ("REVOKED", "application declined"),
        "CLOSED": ("REVOKED", "account closed"),
    }
    if membership_status in mapping:
        status, reason = mapping[membership_status]
        set_agent_status(customer_id, status, reason)


def unprovisioned_customers():
    """Customers with no agent. The zero-orphan rule, made checkable."""
    return query(
        "SELECT * FROM customers WHERE id NOT IN (SELECT customer_id FROM client_agents)")
