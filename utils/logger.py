import logging

# Configure the main logger
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
main_logger = logging.getLogger("main_logger")

# Configure the XML data logger
xml_logger = logging.getLogger("xml_data_logger")
xml_logger.setLevel(logging.DEBUG)

# Create a FileHandler to write XML data to a file
xml_file_handler = logging.FileHandler("xml_data.log")

# Create a formatter for the XML logger
xml_formatter = logging.Formatter("%(asctime)s - %(message)s")
xml_file_handler.setFormatter(xml_formatter)

# Add the FileHandler to the XML logger
xml_logger.addHandler(xml_file_handler)
