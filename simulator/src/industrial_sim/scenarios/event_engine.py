from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml

from industrial_sim.domain.machine import Machine
from industrial_sim.domain.scenario import ScenarioTransition
from industrial_sim.events.operational import OperationalEvent, OperationalEventFactory


@dataclass
class ScenarioOperationalEventEngine:
    event_factory: OperationalEventFactory
    simulator_run_id: UUID
    deterministic_seed: int
    configuration_version: str
    alarm_mapping: dict[str, str]
    alarm_names: dict[str, str]
    _last_alarm_by_instance: dict[str, str] = field(default_factory=dict, init=False, repr=False)
    _last_fault_by_instance: dict[str, str] = field(default_factory=dict, init=False, repr=False)
    _last_maintenance_by_instance: dict[str, str] = field(default_factory=dict, init=False, repr=False)
    _last_recovery_by_instance: dict[str, str] = field(default_factory=dict, init=False, repr=False)

    @classmethod
    def from_config(
        cls,
        simulator_run_id: UUID,
        deterministic_seed: int,
        configuration_version: str,
        mapping_path: str | Path,
        event_factory: OperationalEventFactory | None = None,
    ) -> "ScenarioOperationalEventEngine":
        document: Any = yaml.safe_load(
            Path(mapping_path).read_text(encoding="utf-8")
        )
        mapping = document.get("signal_alarm_mapping", {})
        stage_severity = document.get("stage_severity", {})
        alarm_mapping = {
            f"signal:{key}": value for key, value in mapping.items()
        }
        alarm_mapping.update(
            {f"stage:{key}": value for key, value in stage_severity.items()}
        )
        names = {
            "VIBRATION_HIGH": "Vibration High",
            "TEMPERATURE_HIGH": "Temperature High",
            "PRESSURE_LOW": "Pressure Low",
            "POWER_ABNORMAL": "Abnormal Power Consumption",
            "QUALITY_DEGRADATION": "Quality Degradation",
            "COMMUNICATION_LOST": "Machine Communication Lost",
        }
        return cls(
            event_factory or OperationalEventFactory(),
            simulator_run_id,
            deterministic_seed,
            configuration_version,
            alarm_mapping,
            names,
        )

    def transition_events(
        self,
        machine: Machine,
        transition: ScenarioTransition,
        scenario_id: str,
        scenario_instance_id: str,
        failure_mode_code: str,
        affected_signals: tuple[str, ...],
        correlation_id: str | None,
        generation_sequence_start: int,
        current_state: str,
        intervention_event_id: str | None = None,
    ) -> list[OperationalEvent]:
        events: list[OperationalEvent] = []
        seq = generation_sequence_start
        key = scenario_instance_id
        stage = transition.to_stage.value

        if stage in {"ANOMALY", "CRITICAL"}:
            alarm_code = self._alarm_code(affected_signals)
            severity = self.alarm_mapping.get(f"stage:{stage}", "HIGH")
            alarm = self.event_factory.build(
                self.simulator_run_id,
                machine,
                "AlarmRaised",
                transition.event_time,
                seq,
                self.deterministic_seed,
                self.configuration_version,
                scenario_id=scenario_id,
                scenario_instance_id=scenario_instance_id,
                correlation_id=correlation_id,
                operating_state=current_state,
                alarm_code=alarm_code,
                alarm_name=self.alarm_names[alarm_code],
                severity=severity,
                failure_mode_code=failure_mode_code,
                message=f"Scenario {scenario_id} reached {stage}",
            )
            events.append(alarm)
            self._last_alarm_by_instance[key] = alarm.event_id
            return events

        if stage == "FAILURE":
            causation_id = self._last_alarm_by_instance.get(key)
            fault = self.event_factory.build(
                self.simulator_run_id,
                machine,
                "MachineFaulted",
                transition.event_time,
                seq,
                self.deterministic_seed,
                self.configuration_version,
                scenario_id=scenario_id,
                scenario_instance_id=scenario_instance_id,
                correlation_id=correlation_id,
                causation_id=causation_id,
                operating_state="FAULT",
                fault_code=failure_mode_code,
                failure_mode_code=failure_mode_code,
                severity="CRITICAL",
                message=f"Machine fault caused by scenario {scenario_id}",
            )
            events.append(fault)
            self._last_fault_by_instance[key] = fault.event_id
            seq += 1

            if current_state != "FAULT":
                events.append(
                    self.event_factory.build(
                        self.simulator_run_id,
                        machine,
                        "StateChanged",
                        transition.event_time,
                        seq,
                        self.deterministic_seed,
                        self.configuration_version,
                        scenario_id=scenario_id,
                        scenario_instance_id=scenario_instance_id,
                        correlation_id=correlation_id,
                        causation_id=fault.event_id,
                        operating_state="FAULT",
                        previous_state=current_state,
                        new_state="FAULT",
                        failure_mode_code=failure_mode_code,
                        message="Machine moved to FAULT state",
                    )
                )
            return events

        if stage == "MAINTENANCE":
            alarm_code = self._alarm_code(affected_signals)
            alarm_id = self._last_alarm_by_instance.get(key)
            if alarm_id:
                clear = self.event_factory.build(
                    self.simulator_run_id,
                    machine,
                    "AlarmCleared",
                    transition.event_time,
                    seq,
                    self.deterministic_seed,
                    self.configuration_version,
                    scenario_id=scenario_id,
                    scenario_instance_id=scenario_instance_id,
                    correlation_id=correlation_id,
                    causation_id=intervention_event_id or self._last_fault_by_instance.get(key),
                    alarm_code=alarm_code,
                    alarm_name=self.alarm_names[alarm_code],
                    failure_mode_code=failure_mode_code,
                    message="Scenario alarm cleared for maintenance",
                )
                events.append(clear)
                seq += 1
                self._last_alarm_by_instance.pop(key, None)

            maintenance = self.event_factory.build(
                self.simulator_run_id,
                machine,
                "MachineStopped",
                transition.event_time,
                seq,
                self.deterministic_seed,
                self.configuration_version,
                scenario_id=scenario_id,
                scenario_instance_id=scenario_instance_id,
                correlation_id=correlation_id,
                causation_id=intervention_event_id or self._last_fault_by_instance.get(key),
                operating_state="MAINTENANCE",
                previous_state=current_state,
                new_state="MAINTENANCE",
                is_planned=False,
                message="Machine stopped for scenario maintenance",
            )
            events.append(maintenance)
            self._last_maintenance_by_instance[key] = maintenance.event_id
            return events

        if stage == "RECOVERY":
            recovery = self.event_factory.build(
                self.simulator_run_id,
                machine,
                "MachineRecovered",
                transition.event_time,
                seq,
                self.deterministic_seed,
                self.configuration_version,
                scenario_id=scenario_id,
                scenario_instance_id=scenario_instance_id,
                correlation_id=correlation_id,
                causation_id=self._last_maintenance_by_instance.get(key),
                previous_state=current_state,
                new_state="RECOVERY",
                operating_state="RECOVERY",
                message="Machine entered recovery after maintenance",
            )
            events.append(recovery)
            self._last_recovery_by_instance[key] = recovery.event_id
            return events

        if stage == "BASELINE":
            events.append(
                self.event_factory.build(
                    self.simulator_run_id,
                    machine,
                    "StateChanged",
                    transition.event_time,
                    seq,
                    self.deterministic_seed,
                    self.configuration_version,
                    scenario_id=scenario_id,
                    scenario_instance_id=scenario_instance_id,
                    correlation_id=correlation_id,
                    causation_id=self._last_recovery_by_instance.get(key),
                    operating_state="RUNNING",
                    previous_state=current_state,
                    new_state="RUNNING",
                    message="Machine returned to baseline operation",
                )
            )
            self._last_recovery_by_instance.pop(key, None)
            self._last_maintenance_by_instance.pop(key, None)
            self._last_fault_by_instance.pop(key, None)
        return events

    def _alarm_code(self, signals: tuple[str, ...]) -> str:
        for signal in signals:
            normalized = signal.lower()
            for token in (
                "vibration",
                "temperature",
                "pressure",
                "power",
                "quality",
                "production_rate",
                "throughput",
                "cycle_time",
                "force",
                "torque",
                "position_error",
                "measurement_deviation",
                "fuel_flow_rate",
                "belt_speed",
                "inspection_cycle_time",
            ):
                if token in normalized:
                    return self.alarm_mapping[f"signal:{token}"]
        return "QUALITY_DEGRADATION"
