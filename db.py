import psycopg2
from psycopg2 import OperationalError, InterfaceError

class AutoReconnectDB:
    def __init__(self, max_retries=3, retry_delay=1, **kwargs):
        self.connection_kwargs = kwargs
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.connection = None
        self.connect()
    
    def connect(self):
        """Установить соединение с БД"""
        for attempt in range(self.max_retries):
            try:
                self.connection = psycopg2.connect(**self.connection_kwargs, client_encoding = 'utf8', options='-c client_encoding=utf8')
                self.connection.set_client_encoding('UTF8')
                print("Соединение с БД установлено")
                return
            except OperationalError as e:
                print(f"Попытка {attempt + 1} не удалась: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise
    
    def execute(self, query, params=None, commit=False):
        """Выполнить запрос с автоматическим переподключением"""
        for attempt in range(self.max_retries):
            try:
                if self.connection.closed:
                    self.connect()
                
                with self.connection.cursor() as cursor:
                    cursor.execute(query, params)
                    if commit:
                    	self.connection.commit()
                    return cursor.fetchall() if cursor.description else None
                    
            except (OperationalError, InterfaceError) as e:
                print(f"Ошибка соединения: {e}")
                if attempt < self.max_retries - 1:
                    self.connect()
                    time.sleep(self.retry_delay)
                else:
                    raise
    
    def close(self):
        """Закрыть соединение"""
        if self.connection and not self.connection.closed:
            self.connection.close()

