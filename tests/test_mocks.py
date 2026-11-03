"""The Harnai demo registers: Sagar-4, weather, tide, and schemes."""

from __future__ import annotations

from core.load import load_json


def test_sagar_4_is_the_overdue_harnai_boat():
    boats = {boat["id"]: boat for boat in load_json("boats.json")["boats"]}
    sagar = boats["sagar-4"]
    assert sagar["name"] == "Sagar-4"
    assert sagar["district"] == "Ratnagiri"
    assert sagar["home_port"] == "Harnai"
    assert len(sagar["crew"]) == 3
    assert sagar["licence_no"] == "RTN-FISH-2019-1142"
    assert {"Meerabai", "Chandra-2", "Harnai-Queen"} <= {boat["name"] for boat in boats.values()}


def test_weather_and_tide_name_the_rough_water_clock():
    weather = load_json("weather.json")
    tide = load_json("tide.json")
    assert weather["station"] == "Harnai"
    assert weather["rough_after"] == "16:30"
    assert weather["wind_from_deg"] == 270
    assert tide["current_to_deg"] == 200
    assert tide["tide_state"] == "ebb"
