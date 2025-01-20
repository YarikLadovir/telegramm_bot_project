from aiogram.types import BotCommand
private = [
    BotCommand(command="start", description="о боте"),
    BotCommand(command="tracking", description="отслеживание прогресса"),
    BotCommand(command="report_achievements", description="прогресс в графиках"),
    BotCommand(command="clear", description="очищает историю запросов"),
    BotCommand(command="get_personal_training", description="создает персональную тренировку"),
    BotCommand(command="get_equipment", description="получить совет про экипировку"),
    BotCommand(command="get_nutrition", description="получить совет про питание"),
    BotCommand(command="start_reminders", description="активировать напоминания"),
    BotCommand(command="stop_reminders", description="прекратить напоминания")
]

