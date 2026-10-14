import logging


def configure_logging():
    """Cấu hình root logger (INFO, có timestamp).

    Gọi nhiều lần vô hại: basicConfig bỏ qua nếu root logger đã có handler.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
