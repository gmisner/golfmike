# Flight Plan Consumer Disabled

## Summary
The separate flight plan consumer has been **disabled** because flight plan messages are now handled by the **traffic consumer**.

## Why?
The traffic consumer processes all message types from the TFMS queue, including:
- `flightPlanInformation`
- `FlightCreate`
- `HCS_FLIGHT_PLAN_MSG`
- `FD_FLIGHT_CREATE_MSG`
- `IADE_FLIGHT_PLAN_MSG`

Having a separate consumer was causing:
- Queue shutdown errors
- Duplicate processing
- Unnecessary resource usage

## Changes Made

### 1. Created New Parser & Storer
- **`parsers/flight_plan_traffic_parser.py`** - Parses flight plan messages from traffic consumer
- **`storers/flight_plan_traffic_storer.py`** - Stores flight plans to `flight_plan` and `flights` tables

### 2. Registered Message Types
Updated `parser_storer_registry.py` to handle:
- `flightPlanInformation` → `parse_flight_plan_traffic` → `store_flight_plan_traffic`
- `FlightCreate` → `parse_flight_plan_traffic` → `store_flight_plan_traffic`
- `HCS_FLIGHT_PLAN_MSG` → `parse_flight_plan_traffic` → `store_flight_plan_traffic`
- `FD_FLIGHT_CREATE_MSG` → `parse_flight_plan_traffic` → `store_flight_plan_traffic`
- `IADE_FLIGHT_PLAN_MSG` → `parse_flight_plan_traffic` → `store_flight_plan_traffic`

### 3. Disabled Separate Consumer
- **`tasks.py`** - `start_flight_plan_consumer()` now returns immediately with a log message
- **`.devcontainer/docker-compose.yml`** - Commented out the `flight_plan_consumer` service

## How It Works Now

1. **Traffic Consumer** receives all messages from TFMS queue
2. **swim_data_processor** extracts `msgType` from XML
3. **Parser Registry** routes to `parse_flight_plan_traffic` for flight plan messages
4. **Storer Registry** routes to `store_flight_plan_traffic` to store data
5. Data is stored in:
   - `flight_plan` table (existing structure)
   - `flights` table (new structure with GUFI)
   - Temporary GUFIs are auto-resolved when real GUFIs are found

## Benefits
- ✅ Single consumer handles all message types
- ✅ No duplicate processing
- ✅ Better resource utilization
- ✅ Simpler architecture
- ✅ All flight plans stored in unified `flights` table

## To Re-enable (if needed)
1. Uncomment the `flight_plan_consumer` service in `docker-compose.yml`
2. Update `tasks.py` to actually start the consumer
3. Note: You may need to handle duplicate message processing

