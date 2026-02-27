"""
Parameterized generator for EA2: Coverage Gap.
"""
from __future__ import annotations
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


class Generator(TaskGenerator):
    task_id = "EA2_coverage_gap"
    domain = "Testing"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # Vary variable/function names across seeds
        domains = ["email", "username", "phone_number"]
        domain = domains[seed % len(domains)]

        workspace_files = self._make_workspace(seed, domain)

        spec_md = open(__file__.replace("gen_ea2_coverage_gap.py", "../tasks/EA2_coverage_gap/spec.md")).read()
        brief_md = open(__file__.replace("gen_ea2_coverage_gap.py", "../tasks/EA2_coverage_gap/brief.md")).read()

        return GeneratedTask(
            task_id="EA2_coverage_gap",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={"min_branch_coverage": 90, "seed": seed},
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Testing"},
        )

    def _make_workspace(self, seed: int, domain: str) -> dict:
        files = {}
        # Vary function/module names per seed for cross-seed differentiation
        fn_names = {
            "email": ("validate_email", "email", "@"),
            "username": ("validate_username", "username", "_"),
            "phone_number": ("validate_phone", "phone", "-"),
        }
        fn_name, param_name, sep_char = fn_names[domain]
        files["validator/__init__.py"] = f"from validator.core import {fn_name}, validate_range, validate_string\n"

        files["validator/core.py"] = f'''"""Core validation functions — seed {seed}."""
from typing import Optional


def {fn_name}({param_name}: str) -> bool:
    """Validate {param_name} format."""
    if not {param_name}:
        return False
    if "{sep_char}" not in {param_name}:
        return False
    local, _, rest = {param_name}.partition("{sep_char}")
    if not local:
        return False
    if len(rest) < 2:
        return False
    return True


def validate_range(value: float, minimum: float, maximum: float) -> bool:
    """Validate value is within [minimum, maximum]."""
    if minimum > maximum:
        raise ValueError(f"minimum ({{minimum}}) > maximum ({{maximum}})")
    if value == minimum:
        return True
    if value == maximum:
        return True
    return minimum < value < maximum


def validate_string(value: str, min_length: int = 1, max_length: Optional[int] = None) -> bool:
    """Validate string length and content."""
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    if not stripped:
        return False
    if len(stripped) < min_length:
        return False
    if max_length is None:
        return True
    return len(stripped) <= max_length
'''

        files["validator/rules.py"] = '''"""Validation rule classes."""
from typing import Any, Tuple, Type, Union


class ValidationError(Exception):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class RequiredRule:
    def validate(self, field: str, value: Any) -> None:
        if value is None:
            raise ValidationError(field, "required field is None")
        if isinstance(value, str) and value == "":
            raise ValidationError(field, "required field is empty")


class TypeRule:
    def __init__(self, expected_type: Union[Type, Tuple[Type, ...]]):
        self.expected_type = expected_type

    def validate(self, field: str, value: Any) -> None:
        if isinstance(self.expected_type, tuple):
            if not isinstance(value, self.expected_type):
                raise ValidationError(field, f"expected one of {self.expected_type}")
        elif not isinstance(value, self.expected_type):
            raise ValidationError(field, f"expected {self.expected_type.__name__}")


class PatternRule:
    def __init__(self, pattern: str):
        import re
        self.regex = re.compile(pattern)

    def validate(self, field: str, value: str) -> None:
        if not self.regex.match(value):
            raise ValidationError(field, f"does not match pattern")


class RangeRule:
    def __init__(self, minimum: float, maximum: float, exclusive: bool = False):
        self.minimum = minimum
        self.maximum = maximum
        self.exclusive = exclusive

    def validate(self, field: str, value: Any) -> None:
        if isinstance(value, float):
            pass  # float values allowed
        if self.exclusive:
            if not (self.minimum < value < self.maximum):
                raise ValidationError(field, f"must be strictly between {self.minimum} and {self.maximum}")
        else:
            if not (self.minimum <= value <= self.maximum):
                raise ValidationError(field, f"must be between {self.minimum} and {self.maximum}")
'''

        files["validator/pipeline.py"] = '''"""Validation pipeline."""
from typing import Any, Dict, List
from validator.rules import ValidationError


class Pipeline:
    def __init__(self):
        self._rules: List[tuple] = []

    def add_rule(self, field: str, rule) -> "Pipeline":
        for existing_field, existing_rule in self._rules:
            if existing_field == field and type(existing_rule) == type(rule):
                return self
        self._rules.append((field, rule))
        return self

    def clear(self) -> "Pipeline":
        if not self._rules:
            return self
        self._rules = []
        return self

    def run(self, data: Dict[str, Any]) -> List[ValidationError]:
        if not self._rules:
            return []

        errors = []
        for field, rule in self._rules:
            value = data.get(field)
            try:
                rule.validate(field, value)
            except ValidationError as e:
                errors.append(e)
                break
        else:
            pass

        return errors
'''

        # Minimal existing test (only covers the happy paths)
        files["tests/__init__.py"] = ""
        files["tests/test_basic.py"] = f'''"""Basic tests — only covers happy paths (~40% coverage)."""
from validator.core import {fn_name}, validate_range, validate_string
from validator.rules import RequiredRule, TypeRule, PatternRule, RangeRule, ValidationError
from validator.pipeline import Pipeline


def test_{fn_name}_valid():
    assert {fn_name}("user{sep_char}example{sep_char}com") is True


def test_range_valid():
    assert validate_range(5, 1, 10) is True


def test_string_valid():
    assert validate_string("hello") is True


def test_required_rule_ok():
    rule = RequiredRule()
    rule.validate("name", "Alice")  # No exception = pass


def test_type_rule_ok():
    rule = TypeRule(str)
    rule.validate("name", "Alice")


def test_range_rule_ok():
    rule = RangeRule(0, 100)
    rule.validate("score", 50)


def test_pipeline_basic():
    p = Pipeline()
    p.add_rule("name", RequiredRule())
    errors = p.run({{"name": "Alice"}})
    assert errors == []
'''

        files["requirements.txt"] = "pytest\npytest-cov\ncoverage\n"

        return files
