"""
Celery Beat Schedule Configuration

This file defines periodic tasks for the Celery beat scheduler.
It includes weather data fetching, system health checks, and maintenance tasks.
"""

from celery.schedules import crontab

# Celery Beat Schedule Configuration
beat_schedule = {
    # Fetch weather data from AviationWeather.gov every 15 minutes
    'fetch-aviation-weather': {
        'task': 'tasks.fetch_aviation_weather',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
        'options': {
            'queue': 'weather_processing',
            'priority': 5
        }
    },
    
    # Fetch weather data every hour for comprehensive coverage
    'fetch-aviation-weather-hourly': {
        'task': 'tasks.fetch_aviation_weather',
        'schedule': crontab(minute=0),  # Every hour at minute 0
        'args': ([
            'KLAX', 'KJFK', 'KORD', 'KDFW', 'KATL', 'KSEA', 'KDEN', 
            'KIAH', 'KLAS', 'KMIA', 'KBOS', 'KPHX', 'KMSP', 'KDTW',
            'KPHL', 'KCLT', 'KMCO', 'KTPA', 'KPDX', 'KSLC', 'KMDW',
            'KBWI', 'KSAN', 'KSTL', 'KMCI', 'KAUS', 'KMSY', 'KRSW',
            'KTPA', 'KJAX', 'KSMF', 'KSJC', 'KOAK', 'KSNA', 'KBUR'
        ],),  # Major US airports
        'options': {
            'queue': 'weather_processing',
            'priority': 3
        }
    },
    
    # Test database connection every 5 minutes
    'test-database-connection': {
        'task': 'tasks.test_database_connection',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
        'options': {
            'queue': 'system_health',
            'priority': 1
        }
    },
    
    # Clean up old weather data daily at 2 AM
    'cleanup-old-weather-data': {
        'task': 'tasks.cleanup_old_weather_data',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
        'options': {
            'queue': 'maintenance',
            'priority': 2
        }
    },
}

# Timezone for the beat schedule
timezone = 'UTC'

# Additional beat configuration
beat_config = {
    'beat_schedule': beat_schedule,
    'timezone': timezone,
    'beat_schedule_filename': '/app/celerybeat-schedule',
    'beat_max_loop_interval': 300,  # 5 minutes max loop interval
}


