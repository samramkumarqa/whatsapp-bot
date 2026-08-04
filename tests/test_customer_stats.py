"""
analytics/customer_stats.py's search_customers() backs the dashboard's
conversation search box (see api/customer.py's /customer-search/{user_id}
and templates/dashboard.html's searchCustomers()). It's expected to match
a customer if the query appears in their phone number, their name, or
anywhere in their conversation history - tested here against the
isolated_db fixture with real seeded data rather than mocks.
"""

from crm.customer_mapping import save_customer_number, save_mapping
from conversations import add_message
from analytics.customer_stats import search_customers, get_customer_stats


def _seed_customer(user_id, business_id, business_phone, customer_phone, name, message):
    save_customer_number(user_id, business_phone, business_id)
    save_mapping(
        customer_phone=customer_phone,
        business_phone=business_phone,
        customer_name=name,
    )
    add_message(f"{business_id}:{customer_phone}", "user", message)


def test_search_by_phone_number(isolated_db):
    _seed_customer("u1", "biz1", "+10000000000", "+919962824442", "Saranya S", "hi there")
    _seed_customer("u1", "biz1", "+10000000000", "+916374000275", "Shanthi", "hello")

    results = search_customers("u1", "9962824442")

    assert [c["phone"] for c in results] == ["+919962824442"]


def test_search_by_name_is_case_insensitive(isolated_db):
    _seed_customer("u1", "biz1", "+10000000000", "+919962824442", "Saranya S", "hi there")
    _seed_customer("u1", "biz1", "+10000000000", "+916374000275", "Shanthi", "hello")

    results = search_customers("u1", "saranya")

    assert [c["phone"] for c in results] == ["+919962824442"]


def test_search_by_message_content_matches_full_history_not_just_last_message(isolated_db):
    _seed_customer("u1", "biz1", "+10000000000", "+919962824442", "Saranya S", "what is the price?")
    _seed_customer("u1", "biz1", "+10000000000", "+916374000275", "Shanthi", "hello there")

    # A second, more recent message from the same customer - last_message
    # in get_customer_stats() would only be this one, not the earlier
    # "price" message, so this proves search covers the whole thread.
    add_message("biz1:+919962824442", "assistant", "Our course starts Monday")

    results = search_customers("u1", "price")

    assert [c["phone"] for c in results] == ["+919962824442"]


def test_search_empty_query_returns_everyone(isolated_db):
    _seed_customer("u1", "biz1", "+10000000000", "+919962824442", "Saranya S", "hi")
    _seed_customer("u1", "biz1", "+10000000000", "+916374000275", "Shanthi", "hello")

    all_customers = get_customer_stats("u1")
    results = search_customers("u1", "")

    assert len(results) == len(all_customers) == 2


def test_search_no_match_returns_empty_list(isolated_db):
    _seed_customer("u1", "biz1", "+10000000000", "+919962824442", "Saranya S", "hi")

    assert search_customers("u1", "zzzznomatchzzzz") == []


def test_search_unknown_user_returns_empty_list(isolated_db):
    assert search_customers("no-such-user", "anything") == []
