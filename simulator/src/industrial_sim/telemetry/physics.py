from __future__ import annotations

from dataclasses import dataclass

from industrial_sim.telemetry.base import TelemetryPhysics, TelemetryPhysicsContext
from industrial_sim.telemetry.noise import (
    DeterministicNoise,
    ambient_delta,
    degradation_factor,
    load_factor,
    running_scale,
)


def bounded(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def base_factors(context: TelemetryPhysicsContext) -> tuple[float, float, float, DeterministicNoise]:
    bc = context.behavior_context
    load = load_factor(bc.workload_factor)
    wear = degradation_factor(bc.health_factor, bc.scenario_severity)
    active = running_scale(context.machine.state.value)
    noise = DeterministicNoise(context.machine.machine_type, context.machine.machine_id, context.event_time)
    return load, wear, active, noise


@dataclass(frozen=True)
class CNCPhysics:
    machine_type: str = "CNC"

    def generate(self, context: TelemetryPhysicsContext) -> dict[str, float]:
        load, wear, active, n = base_factors(context)
        temp = 30 + 24 * load + 12 * wear + 0.35 * ambient_delta(context.behavior_context.ambient_temperature_c)
        vibration = 1.1 + 2.3 * load + 4.8 * wear
        spindle = active * (650 + 7000 * load)
        feed = active * (180 + 1650 * load)
        pressure = 78 + 26 * load - 30 * wear
        power = 5 + 40 * load + 14 * wear
        rate = active * max(0.0, 24 * load * (1 - 0.38 * wear))
        quality = 99 - 7.0 * wear - 1.2 * max(0.0, load - 1.0)
        return {
            "spindle_rpm": bounded(spindle + n.gaussian("spindle", stddev=40), 0, 30000),
            "vibration_mm_s": bounded(vibration + n.gaussian("vibration", stddev=0.16), 0, 100),
            "temperature_c": bounded(temp + n.gaussian("temperature", stddev=0.35), -40, 250),
            "pressure_bar": bounded(pressure + n.gaussian("pressure", stddev=0.9), 0, 500),
            "power_kw": bounded(power + n.gaussian("power", stddev=0.45), 0, 1000),
            "feed_rate_mm_min": bounded(feed + n.gaussian("feed", stddev=10), 0, 10000),
            "production_rate_unit_min": bounded(rate + n.gaussian("rate", stddev=0.18), 0, 1000),
            "quality_score_pct": bounded(quality + n.gaussian("quality", stddev=0.08), 0, 100),
        }


@dataclass(frozen=True)
class HydraulicPressPhysics:
    machine_type: str = "HYDRAULIC_PRESS"

    def generate(self, context: TelemetryPhysicsContext) -> dict[str, float]:
        load, wear, active, n = base_factors(context)
        pressure = 130 + 38 * load - 34 * wear
        temp = 31 + 20 * load + 13 * wear + 0.28 * ambient_delta(context.behavior_context.ambient_temperature_c)
        force = active * (160 + 700 * load + 220 * wear)
        cycle = 8.0 + 1.8 * load + 4.8 * wear
        power = 9 + 43 * load + 18 * wear
        rate = active * max(0.0, 7.5 * load * (1 - 0.42 * wear))
        quality = 99 - 8.0 * wear
        return {
            "hydraulic_pressure_bar": bounded(pressure + n.gaussian("pressure", stddev=1.0), 0, 500),
            "temperature_c": bounded(temp + n.gaussian("temperature", stddev=0.45), -40, 250),
            "force_kn": bounded(force + n.gaussian("force", stddev=5), 0, 5000),
            "cycle_time_s": bounded(cycle + n.gaussian("cycle", stddev=0.06), 0, 3600),
            "power_kw": bounded(power + n.gaussian("power", stddev=0.5), 0, 1000),
            "production_rate_unit_min": bounded(rate + n.gaussian("rate", stddev=0.06), 0, 1000),
            "quality_score_pct": bounded(quality + n.gaussian("quality", stddev=0.06), 0, 100),
        }


@dataclass(frozen=True)
class IndustrialRobotPhysics:
    machine_type: str = "INDUSTRIAL_ROBOT"

    def generate(self, context: TelemetryPhysicsContext) -> dict[str, float]:
        load, wear, active, n = base_factors(context)
        motor_temp = 29 + 18 * load + 15 * wear + 0.30 * ambient_delta(context.behavior_context.ambient_temperature_c)
        torque = active * (65 + 165 * load + 125 * wear)
        vibration = 0.8 + 1.7 * load + 4.3 * wear
        position_error = 0.035 + 0.09 * wear + 0.12 * max(0.0, load - 1.0)
        cycle = 4.5 + 0.8 * load + 1.7 * wear
        power = 4 + 15 * load + 8 * wear
        rate = active * max(0.0, 14 * load * (1 - 0.28 * wear))
        return {
            "motor_temperature_c": bounded(motor_temp + n.gaussian("motor_temp", stddev=0.28), -40, 250),
            "torque_nm": bounded(torque + n.gaussian("torque", stddev=2.0), 0, 5000),
            "vibration_mm_s": bounded(vibration + n.gaussian("vibration", stddev=0.08), 0, 100),
            "position_error_mm": bounded(position_error + abs(n.gaussian("position", stddev=0.008)), 0, 100),
            "cycle_time_s": bounded(cycle + n.gaussian("cycle", stddev=0.04), 0, 3600),
            "power_kw": bounded(power + n.gaussian("power", stddev=0.18), 0, 1000),
            "production_rate_unit_min": bounded(rate + n.gaussian("rate", stddev=0.06), 0, 1000),
        }


@dataclass(frozen=True)
class ConveyorPhysics:
    machine_type: str = "CONVEYOR"

    def generate(self, context: TelemetryPhysicsContext) -> dict[str, float]:
        load, wear, active, n = base_factors(context)
        speed = active * (0.35 + 1.05 * load - 0.25 * wear)
        current = 22 + 35 * load + 23 * wear
        vibration = 0.75 + 1.25 * load + 3.9 * wear
        temp = 28 + 15 * load + 13 * wear + 0.25 * ambient_delta(context.behavior_context.ambient_temperature_c)
        power = 3 + 14 * load + 10 * wear
        throughput = active * max(0.0, 33 * load * (1 - 0.38 * wear))
        return {
            "motor_current_a": bounded(current + n.gaussian("current", stddev=0.7), 0, 1000),
            "belt_speed_m_s": bounded(speed + n.gaussian("speed", stddev=0.018), 0, 20),
            "vibration_mm_s": bounded(vibration + n.gaussian("vibration", stddev=0.07), 0, 100),
            "temperature_c": bounded(temp + n.gaussian("temperature", stddev=0.35), -40, 250),
            "power_kw": bounded(power + n.gaussian("power", stddev=0.25), 0, 1000),
            "throughput_unit_min": bounded(throughput + n.gaussian("throughput", stddev=0.12), 0, 1000),
        }


@dataclass(frozen=True)
class CompressorPhysics:
    machine_type: str = "COMPRESSOR"

    def generate(self, context: TelemetryPhysicsContext) -> dict[str, float]:
        load, wear, active, n = base_factors(context)
        pressure = 7.0 + 4.2 * load - 2.2 * wear
        temp = 31 + 21 * load + 14 * wear + 0.30 * ambient_delta(context.behavior_context.ambient_temperature_c)
        vibration = 0.95 + 1.5 * load + 4.2 * wear
        rpm = active * (900 + 2500 * load)
        power = 10 + 27 * load + 12 * wear
        return {
            "discharge_pressure_bar": bounded(pressure + n.gaussian("pressure", stddev=0.06), 0, 500),
            "temperature_c": bounded(temp + n.gaussian("temperature", stddev=0.4), -40, 250),
            "vibration_mm_s": bounded(vibration + n.gaussian("vibration", stddev=0.08), 0, 100),
            "rpm": bounded(rpm + n.gaussian("rpm", stddev=10), 0, 30000),
            "power_kw": bounded(power + n.gaussian("power", stddev=0.35), 0, 1000),
        }


@dataclass(frozen=True)
class FurnacePhysics:
    machine_type: str = "FURNACE"

    def generate(self, context: TelemetryPhysicsContext) -> dict[str, float]:
        load, wear, _, n = base_factors(context)
        chamber = 780 + 220 * load + 190 * wear + 4.0 * ambient_delta(context.behavior_context.ambient_temperature_c)
        fuel = 28 + 36 * load + 15 * wear
        pressure = 980 + 58 * load - 115 * wear
        power = 100 + 130 * load + 46 * wear
        cycle = 42 + 8 * load + 6 * wear
        quality = 99 - 6.5 * wear
        return {
            "chamber_temperature_c": bounded(chamber + n.gaussian("chamber_temp", stddev=2.5), 0, 2500),
            "fuel_flow_rate": bounded(fuel + n.gaussian("fuel", stddev=0.7), 0, 1000),
            "pressure_mbar": bounded(pressure + n.gaussian("pressure", stddev=2.5), 0, 5000),
            "power_kw": bounded(power + n.gaussian("power", stddev=1.0), 0, 1000),
            "cycle_time_s": bounded(cycle + n.gaussian("cycle", stddev=0.15), 0, 3600),
            "quality_score_pct": bounded(quality + n.gaussian("quality", stddev=0.05), 0, 100),
        }


@dataclass(frozen=True)
class InspectionPhysics:
    machine_type: str = "INSPECTION"

    def generate(self, context: TelemetryPhysicsContext) -> dict[str, float]:
        load, wear, _, n = base_factors(context)
        cycle = 7 + 2.0 * load + 5.0 * wear
        deviation = 0.025 + 0.085 * wear + 0.03 * max(0.0, load - 1.0)
        probability = 1.2 + 18 * wear + 4 * max(0.0, load - 1.0)
        temp = 23 + 8 * load + 7 * wear + 0.18 * ambient_delta(context.behavior_context.ambient_temperature_c)
        return {
            "inspection_cycle_time_s": bounded(cycle + n.gaussian("cycle", stddev=0.04), 0, 3600),
            "measurement_deviation_mm": bounded(deviation + abs(n.gaussian("deviation", stddev=0.003)), 0, 100),
            "defect_probability_pct": bounded(probability + n.gaussian("probability", stddev=0.2), 0, 100),
            "equipment_temperature_c": bounded(temp + n.gaussian("temperature", stddev=0.15), -40, 250),
        }


@dataclass(frozen=True)
class PackagingPhysics:
    machine_type: str = "PACKAGING"

    def generate(self, context: TelemetryPhysicsContext) -> dict[str, float]:
        load, wear, active, n = base_factors(context)
        cycle = 3.2 + 0.8 * load + 2.5 * wear
        throughput = active * max(0.0, 28 * load * (1 - 0.34 * wear))
        current = 18 + 28 * load + 20 * wear
        temp = 27 + 13 * load + 12 * wear + 0.25 * ambient_delta(context.behavior_context.ambient_temperature_c)
        power = 4 + 12 * load + 8 * wear
        return {
            "cycle_time_s": bounded(cycle + n.gaussian("cycle", stddev=0.035), 0, 3600),
            "throughput_unit_min": bounded(throughput + n.gaussian("throughput", stddev=0.1), 0, 1000),
            "motor_current_a": bounded(current + n.gaussian("current", stddev=0.6), 0, 1000),
            "temperature_c": bounded(temp + n.gaussian("temperature", stddev=0.3), -40, 250),
            "power_kw": bounded(power + n.gaussian("power", stddev=0.22), 0, 1000),
        }


@dataclass(frozen=True)
class PalletizerPhysics:
    machine_type: str = "PALLETIZER"

    def generate(self, context: TelemetryPhysicsContext) -> dict[str, float]:
        load, wear, _, n = base_factors(context)
        cycle = 7 + 1.2 * load + 2.8 * wear
        motor_temp = 30 + 16 * load + 14 * wear + 0.28 * ambient_delta(context.behavior_context.ambient_temperature_c)
        torque = 80 + 170 * load + 130 * wear
        vibration = 1.0 + 1.5 * load + 4.4 * wear
        power = 5 + 16 * load + 9 * wear
        return {
            "cycle_time_s": bounded(cycle + n.gaussian("cycle", stddev=0.05), 0, 3600),
            "motor_temperature_c": bounded(motor_temp + n.gaussian("motor_temp", stddev=0.25), -40, 250),
            "torque_nm": bounded(torque + n.gaussian("torque", stddev=2.5), 0, 5000),
            "vibration_mm_s": bounded(vibration + n.gaussian("vibration", stddev=0.08), 0, 100),
            "power_kw": bounded(power + n.gaussian("power", stddev=0.25), 0, 1000),
        }


PHYSICS_BY_TYPE: dict[str, TelemetryPhysics] = {
    "CNC": CNCPhysics(),
    "HYDRAULIC_PRESS": HydraulicPressPhysics(),
    "INDUSTRIAL_ROBOT": IndustrialRobotPhysics(),
    "CONVEYOR": ConveyorPhysics(),
    "COMPRESSOR": CompressorPhysics(),
    "FURNACE": FurnacePhysics(),
    "INSPECTION": InspectionPhysics(),
    "PACKAGING": PackagingPhysics(),
    "PALLETIZER": PalletizerPhysics(),
}


def generate_type_telemetry(
    machine,
    behavior_context,
    event_time,
) -> dict[str, float]:
    try:
        provider = PHYSICS_BY_TYPE[machine.machine_type]
    except KeyError as exc:
        raise KeyError(f"No telemetry physics registered for {machine.machine_type}") from exc
    return provider.generate(
        TelemetryPhysicsContext(
            machine=machine,
            behavior_context=behavior_context,
            event_time=event_time,
        )
    )
