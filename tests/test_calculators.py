import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.features.calculators import (
    calculate_notice_period,
    calculate_alimony_renard,
    calculate_succession_duties,
)


class TestNoticePeriod:
    def test_basic_notice(self):
        result = calculate_notice_period(years=5, monthly_salary=3000)
        assert result["details"]["weeks"] == 18
        assert "CCT n" in result["legal_basis"]

    def test_zero_years(self):
        result = calculate_notice_period(years=0, monthly_salary=2500)
        assert result["details"]["weeks"] >= 1

    def test_long_service(self):
        result = calculate_notice_period(years=25, monthly_salary=4000)
        assert result["details"]["weeks"] >= 60

    def test_negative_years_raises(self):
        with pytest.raises(ValueError):
            calculate_notice_period(years=-1, monthly_salary=3000)

    def test_indemnity_positive(self):
        result = calculate_notice_period(years=10, monthly_salary=3500)
        assert result["result"] > 0


class TestAlimonyRenard:
    def test_basic_alimony(self):
        result = calculate_alimony_renard(income_high=4000, income_low=1500, children=2)
        assert result["result"] > 0
        assert "formula" in result["details"]

    def test_no_children(self):
        result = calculate_alimony_renard(income_high=3000, income_low=1000, children=0)
        assert result["result"] > 0

    def test_swapped_incomes(self):
        r1 = calculate_alimony_renard(income_high=4000, income_low=1000)
        r2 = calculate_alimony_renard(income_high=1000, income_low=4000)
        assert r1["result"] == r2["result"]

    def test_cap_applied(self):
        result = calculate_alimony_renard(income_high=2000, income_low=0, children=5)
        assert result["result"] <= 2000 / 3 + 1


class TestSuccessionDuties:
    def test_brussels_direct_line(self):
        result = calculate_succession_duties(region="bruxelles", amount=200000, relationship="direct_line")
        assert result["result"] > 0
        assert result["details"]["region"] == "bruxelles"

    def test_wallonia_direct_line(self):
        result = calculate_succession_duties(region="wallonie", amount=200000, relationship="direct_line")
        assert result["result"] > 0

    def test_flanders_direct_line(self):
        result = calculate_succession_duties(region="flandre", amount=200000, relationship="direct_line")
        assert result["result"] > 0

    def test_net_amount_correct(self):
        result = calculate_succession_duties(region="bruxelles", amount=100000, relationship="direct_line")
        assert result["details"]["net_amount"] == round(100000 - result["result"], 2)

    def test_invalid_region(self):
        with pytest.raises(ValueError):
            calculate_succession_duties(region="paris", amount=100000)

    def test_breakdown_sums_to_total(self):
        result = calculate_succession_duties(region="wallonie", amount=300000, relationship="direct_line")
        breakdown_sum = sum(b["duty"] for b in result["details"]["breakdown"])
        assert abs(breakdown_sum - result["result"]) < 0.01
