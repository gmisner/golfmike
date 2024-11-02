# testdb.py
from swim_data_processor import parse_and_store_to_database
from utils.logger import main_logger as logger

# Sample XML string to test
xml_string = """
<root msgType="TMI_FLIGHT_LIST">
    <fiOutput>
        <flight>
            <aircraft_id>N12346</aircraft_id>
            <gufi>G12345</gufi>
            <igtd>2024-10-13T12:00:00Z</igtd>
            <departure_airport>JFK</departure_airport>
            <arrival_airport>LAX</arrival_airport>
        </flight>
    </fiOutput>
</root>
"""

if __name__ == "__main__":
    logger.info("Starting test database storage")
    result = parse_and_store_to_database(xml_string)
    if result:
        logger.success("Test database storage successful")
    else:
        logger.error("Test database storage failed")
