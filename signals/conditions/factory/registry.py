"""Factory registry for condition profiles."""

from signals.conditions.public.factory import PublicExampleFactory


def get_condition_factory(profile: str):
    normalized = (profile or "").strip().lower()
    if normalized in ("", "private_condition", "ma", "base", "private_ma"):
        try:
            from signals.conditions.private.factory import PrivateMAConditionFactory
        except Exception as exc:
            raise ValueError("private_condition profile is unavailable in this repository") from exc
        return PrivateMAConditionFactory()
    if normalized in ("public_example", "example"):
        return PublicExampleFactory()
    if normalized in ("private_vwap", "public_vwap"):
        try:
            from signals.conditions.private.factory import PrivateVwapFactory
        except Exception as exc:
            raise ValueError("private_vwap profile is unavailable in this repository") from exc
        return PrivateVwapFactory()
    if normalized in ("private_gate_vwap", "private_vwap_mix", "public_vwap_ma"):
        try:
            from signals.conditions.private.factory import PrivateLongGateVwapFactory
        except Exception as exc:
            raise ValueError("private_gate_vwap profile is unavailable in this repository") from exc
        return PrivateLongGateVwapFactory()

    raise ValueError("Unknown condition profile: {}".format(profile))
