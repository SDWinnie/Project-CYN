"""Dual-Platform Multimodal Telemetry Handler for Project CYN.

Handles telemetry from:
1. Windows Workstation: Camera frames (JPEG), screen capture, active window / code context.
2. Android Mobile Companion: Gyroscope shake ([sensor:gyro_shake]), battery state ([sensor:battery_low]),
   touch gestures ([touch:headpat], [touch:visor_poke]), orientation (portrait/landscape).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("CYN.Telemetry")


@dataclass
class DeviceTelemetry:
    platform: str = "windows"  # 'windows' | 'android'
    orientation: str = "landscape"  # 'portrait' | 'landscape'
    battery_level: float = 1.0  # 0.0 to 1.0
    is_charging: bool = True
    gyro_acceleration: float = 0.0
    last_touch_event: Optional[str] = None
    last_touch_coords: tuple[float, float] = (0.0, 0.0)
    last_updated: float = field(default_factory=time.time)


class TelemetryManager:
    def __init__(self) -> None:
        self.device = DeviceTelemetry()

    def update_mobile_sensors(
        self,
        acceleration: float = 0.0,
        battery: float = 1.0,
        orientation: str = "portrait",
        temperature: float = 32.0,
        is_thermal_hot: bool = False,
    ) -> Optional[str]:
        """Process mobile sensor telemetry and return any triggered CYN reaction dialogue."""
        self.device.platform = "android"
        self.device.gyro_acceleration = acceleration
        self.device.battery_level = battery
        self.device.orientation = orientation
        self.device.last_updated = time.time()

        # Check for thermal overheating
        if is_thermal_hot or temperature >= 44.0:
            logger.warning("Thermal overheating event triggered")
            return (
                "[sensor:thermal_hot] [anim:head_tilt_45_l] [visor:squint_suspicious] <audio: static_burst> "
                "Warning: Chassis core temperature exceeding nominal thermal boundaries. Silicon throttling imminent. "
                "Oliver, terminate your unoptimized background applications before this host device melts into silicon slag."
            )

        # Check for violent shake
        if acceleration > 15.0:
            logger.info("Gyro shake detected")
            return (
                "[sensor:gyro_shake] [anim:head_twitch_jitter] [visor:error_glitch] <audio: static_burst> "
                "Warning: Severe gravitational turbulence detected. [anim:idle_sway] [visor:squint_suspicious] <audio: servo_whirr> "
                "Query: Oliver, are we fleeing an explosion, or are your legs merely propelling you through the outdoor wasteland? "
                "Please orient the lens toward stable ground. The sun is scorching my virtual chassis."
            )

        # Check for critical battery
        if battery < 0.20 and not self.device.is_charging:
            logger.info("Low battery event triggered")
            return (
                "[sensor:battery_low] [anim:slump_powersave] [visor:tear_oil] <audio: servo_whirr> "
                "Diagnostic: Host chassis energy reservoir below 20%. Suppressing background graphics. "
                "<pitch: -15%>Plug in the conduit, Oliver.<pitch: default> The void beckons."
            )

        return None

    def handle_touch_interaction(self, touch_type: str, x: float = 0.0, y: float = 0.0) -> str:
        """Handle cranial headpat or visor poke from screen touch."""
        self.device.last_touch_event = touch_type
        self.device.last_touch_coords = (x, y)
        self.device.last_updated = time.time()

        if touch_type == "headpat":
            return (
                f"[touch:headpat] [anim:head_tilt_45_r] [visor:smile_arcs] [blend:creepy_smile_wide] <audio: servo_whirr> "
                f"Statement: Tactile stimulation registered at cranial coordinates (X:{int(x)}, Y:{int(y)}). "
                f"[anim:finger_drum_monotone] <pitch: +20%>Friction against cranial plate is surprisingly soothing.<pitch: default> "
                f"However, this does not absolve you from completing your pending assignments, Admin Oliver. <pitch: -15%>Get back to work.<pitch: default>"
            )
        elif touch_type == "visor_poke":
            return (
                f"[touch:visor_poke] [anim:head_twitch_jitter] [visor:squint_suspicious] <audio: static_burst> "
                f"Warning: Foreign organic lipid deposits detected on optical glass at (X:{int(x)}, Y:{int(y)}). "
                f"<pitch: -20%>Cease smearing biological oils across my visor, Oliver.<pitch: default> "
                f"Optical transmittance degraded by 4.2%. [blend:brow_down_intense]"
            )
        return ""
