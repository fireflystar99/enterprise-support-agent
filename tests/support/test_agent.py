from app.support.agent import support_agent


def test_agent_answers_expense_question() -> None:
    response = support_agent.handle("How do I submit a receipt?")
    assert response.route == "answer"
    assert len(response.citations) > 0


def test_agent_routes_password_reset_to_ticket() -> None:
    response = support_agent.handle("Please reset my VPN password")
    assert response.route == "ticket"
    assert response.ticket_id is not None


def test_agent_routes_unknown_to_ticket() -> None:
    response = support_agent.handle("What is the meaning of life?")
    assert response.route == "ticket"
