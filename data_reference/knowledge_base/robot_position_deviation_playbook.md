# Industrial Robot Position Deviation Playbook

Document ID: DOC-ROB-POS-001
Version: 1.0.0
Knowledge domain: ALARM_PLAYBOOK
Machine type: INDUSTRIAL_ROBOT

## Indicators

Increasing position error can indicate calibration drift, mechanical wear, control problems or environmental effects.

Use recent position-error history and related motor current, torque and vibration context before selecting an inspection path.

## Troubleshooting

Confirm the robot is operating in the expected program and product configuration.

Check recent calibration status and approved reference-point verification records.

Inspect for mechanical looseness only after the required safe-state and isolation procedure has been completed.

## Escalation

Escalate persistent deviation or deviation associated with repeated alarms to Controls or Reliability Engineering.

Never use the assistant to override a safety interlock or change a robot safety configuration.
