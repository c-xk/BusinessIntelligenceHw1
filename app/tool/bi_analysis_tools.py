import os
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

from app.exceptions import ToolError
from app.tool.base import BaseTool, ToolResult

# 使用支持中文的字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'Arial']  # 优先使用中文字体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

load_dotenv()
host = os.getenv("HOST", "localhost")
port = os.getenv("PORT", "27017")
database = os.getenv("DATABASE", "wordtrail")
username = os.getenv("USER_NAME", "")
password = os.getenv("PASSWORD", "")
auth_db = os.getenv("AUTH_DB", "admin")


def get_mongo_connection():
    """获取MongoDB连接"""
    if username and password:
        uri = f"mongodb://{username}:{password}@{host}:{port}/{database}?authSource={auth_db}"
    else:
        uri = f"mongodb://{host}:{port}/{database}"
    client = MongoClient(uri)
    return client


def get_mongo_database():
    """获取MongoDB数据库"""
    client = get_mongo_connection()
    return client[database]


class CollectionBasicInfoTool(BaseTool):
    name: str = "collection_basic_info"
    description: str = "列出所有集合并显示基本统计信息，如文档数量、平均大小等"

    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    async def execute(self, **kwargs) -> ToolResult:
        try:
            db = get_mongo_database()
            collections = db.list_collection_names()

            if not collections:
                return ToolResult(output="数据库中没有找到任何集合")

            result = "数据库集合统计信息:\n"
            for coll_name in collections:
                collection = db[coll_name]
                stats = db.command("collStats", coll_name)
                doc_count = collection.count_documents({})
                avg_obj_size = stats.get("avgObjSize", 0)

                result += f"\n集合: {coll_name}\n"
                result += f"- 文档数量: {doc_count}\n"
                result += f"- 平均文档大小: {avg_obj_size} 字节\n"
                result += f"- 总存储大小: {stats.get('size', 0) / 1024:.2f} KB\n"

            return ToolResult(output=result)
        except Exception as e:
            raise ToolError(str(e))


class WordStatisticsTool(BaseTool):
    name: str = "word_statistics"
    description: str = "分析单词集合，统计各种属性，如难度等级分布、词性分布、标签分布等"

    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "language": {
                "type": "string",
                "description": "语言筛选，例如 'de' 表示德语"
            },
            "tag": {
                "type": "string",
                "description": "标签筛选，例如 'A1' 或 '家具'"
            }
        },
        "required": [],
    }

    async def execute(self, **kwargs) -> ToolResult:
        language = kwargs.get("language")
        tag = kwargs.get("tag")

        try:
            db = get_mongo_database()
            collection = db["words"]

            # 构建查询条件
            query = {}
            if language:
                query["language"] = language
            if tag:
                query["tags"] = tag

            # 获取单词数据
            words = list(collection.find(query))

            if not words:
                return ToolResult(output=f"未找到符合条件的单词 (language={language}, tag={tag})")

            # 分析统计
            result = f"单词统计分析 (总计 {len(words)} 个单词):\n\n"

            # 1. 按难度级别统计
            difficulty_counts = {}
            for word in words:
                difficulty = word.get("difficulty", "unknown")
                if difficulty in difficulty_counts:
                    difficulty_counts[difficulty] += 1
                else:
                    difficulty_counts[difficulty] = 1

            result += "难度级别分布:\n"
            for difficulty, count in sorted(difficulty_counts.items()):
                result += f"- 级别 {difficulty}: {count} 个单词 ({count/len(words)*100:.1f}%)\n"

            # 2. 按词性统计
            pos_counts = {}
            for word in words:
                pos_list = word.get("partOfSpeechList", [])
                for pos_info in pos_list:
                    pos_type = pos_info.get("type", "unknown")
                    if pos_type in pos_counts:
                        pos_counts[pos_type] += 1
                    else:
                        pos_counts[pos_type] = 1

            result += "\n词性分布:\n"
            for pos, count in sorted(pos_counts.items(), key=lambda x: x[1], reverse=True):
                result += f"- {pos}: {count} 个单词 ({count/len(words)*100:.1f}%)\n"

            # 3. 按标签统计
            tag_counts = {}
            for word in words:
                tags = word.get("tags", [])
                for tag in tags:
                    if tag in tag_counts:
                        tag_counts[tag] += 1
                    else:
                        tag_counts[tag] = 1

            result += "\n标签分布 (前10个):\n"
            for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                result += f"- {tag}: {count} 个单词 ({count/len(words)*100:.1f}%)\n"

            # 4. 其他统计信息
            synonym_count = sum(len(word.get("synonyms", [])) for word in words)
            antonym_count = sum(len(word.get("antonyms", [])) for word in words)

            result += f"\n其他统计:\n"
            result += f"- 平均每个单词的同义词数量: {synonym_count/len(words):.2f}\n"
            result += f"- 平均每个单词的反义词数量: {antonym_count/len(words):.2f}\n"

            # 5. 单词样例
            result += f"\n单词样例 (前5个):\n"
            for i, word in enumerate(words[:5]):
                result += f"{i+1}. {word.get('word', 'unknown')}"
                if "partOfSpeechList" in word and word["partOfSpeechList"]:
                    first_pos = word["partOfSpeechList"][0]
                    if "definitions" in first_pos and first_pos["definitions"]:
                        result += f" - {first_pos['definitions'][0]}"
                result += "\n"

            return ToolResult(output=result)
        except Exception as e:
            raise ToolError(str(e))


class LearningProgressAnalysisTool(BaseTool):
    name: str = "learning_progress_analysis"
    description: str = "分析用户的学习进度，包括掌握程度、记忆曲线等"

    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "用户ID"
            },
            "period": {
                "type": "string",
                "description": "时间段，如 'week', 'month', 'all'"
            }
        },
        "required": ["user_id"],
    }

    async def execute(self, **kwargs) -> ToolResult:
        user_id = kwargs.get("user_id")
        period = kwargs.get("period", "all")

        try:
            db = get_mongo_database()
            progress_collection = db["word_learning_progress"]
            words_collection = db["words"]

            # 构建查询条件
            query = {"userId": user_id}

            # 根据时间段筛选
            if period != "all":
                now = datetime.now()
                if period == "week":
                    start_date = now - timedelta(days=7)
                elif period == "month":
                    start_date = now - timedelta(days=30)
                else:
                    start_date = now - timedelta(days=90)  # 默认为3个月

                query["lastReviewTime"] = {"$gte": start_date}

            # 获取学习进度数据
            progress_records = list(progress_collection.find(query))

            if not progress_records:
                return ToolResult(output=f"未找到用户 {user_id} 的学习进度记录")

            # 1. 总体统计
            result = f"用户 {user_id} 的学习进度分析 (总计 {len(progress_records)} 个单词):\n\n"

            # 2. 熟练度分布
            proficiency_levels = {
                "精通 (0.8-1.0)": 0,
                "熟练 (0.6-0.8)": 0,
                "掌握 (0.4-0.6)": 0,
                "学习中 (0.2-0.4)": 0,
                "初学 (0.0-0.2)": 0
            }

            for record in progress_records:
                prof = record.get("proficiency", 0)
                if prof >= 0.8:
                    proficiency_levels["精通 (0.8-1.0)"] += 1
                elif prof >= 0.6:
                    proficiency_levels["熟练 (0.6-0.8)"] += 1
                elif prof >= 0.4:
                    proficiency_levels["掌握 (0.4-0.6)"] += 1
                elif prof >= 0.2:
                    proficiency_levels["学习中 (0.2-0.4)"] += 1
                else:
                    proficiency_levels["初学 (0.0-0.2)"] += 1

            result += "熟练度分布:\n"
            for level, count in proficiency_levels.items():
                result += f"- {level}: {count} 个单词 ({count/len(progress_records)*100:.1f}%)\n"

            # 3. 复习阶段分布
            stage_counts = {}
            for record in progress_records:
                stage = record.get("reviewStage", 0)
                if stage in stage_counts:
                    stage_counts[stage] += 1
                else:
                    stage_counts[stage] = 1

            result += "\n复习阶段分布:\n"
            for stage, count in sorted(stage_counts.items()):
                result += f"- 阶段 {stage}: {count} 个单词 ({count/len(progress_records)*100:.1f}%)\n"

            # 4. 记忆效果分析
            total_reviews = 0
            successful_reviews = 0

            for record in progress_records:
                history = record.get("reviewHistory", [])
                for review in history:
                    total_reviews += 1
                    if review.get("remembered", False):
                        successful_reviews += 1

            success_rate = (successful_reviews / total_reviews * 100) if total_reviews > 0 else 0
            result += f"\n记忆效果分析:\n"
            result += f"- 总复习次数: {total_reviews}\n"
            result += f"- 成功记忆次数: {successful_reviews}\n"
            result += f"- 记忆成功率: {success_rate:.1f}%\n"

            # 5. 学习时间分析
            now = datetime.now()
            time_analysis = {
                "今天": 0,
                "本周": 0,
                "本月": 0,
                "更早": 0
            }

            for record in progress_records:
                last_review = record.get("lastReviewTime")
                if not last_review:
                    continue

                if isinstance(last_review, datetime):
                    days_diff = (now - last_review).days
                    if days_diff < 1:
                        time_analysis["今天"] += 1
                    elif days_diff < 7:
                        time_analysis["本周"] += 1
                    elif days_diff < 30:
                        time_analysis["本月"] += 1
                    else:
                        time_analysis["更早"] += 1

            result += f"\n最近学习情况:\n"
            for period, count in time_analysis.items():
                result += f"- {period}复习: {count} 个单词\n"

            # 6. 获取几个表现最好的单词
            top_words = sorted(progress_records, key=lambda x: x.get("proficiency", 0), reverse=True)[:5]
            result += f"\n掌握最好的单词:\n"

            for i, record in enumerate(top_words):
                word_id = record.get("wordId", {}).get("$oid")
                proficiency = record.get("proficiency", 0)

                word_info = words_collection.find_one({"_id": {"$oid": word_id}}) if word_id else None
                word_text = word_info.get("word", "未知单词") if word_info else "未知单词"

                result += f"{i+1}. {word_text} (熟练度: {proficiency:.2f})\n"

            return ToolResult(output=result)
        except Exception as e:
            raise ToolError(str(e))


class UserLearningGoalsTool(BaseTool):
    name: str = "user_learning_goals"
    description: str = "分析用户的学习目标和实际完成情况"

    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "用户ID"
            },
            "days": {
                "type": "integer",
                "description": "分析最近多少天的数据"
            }
        },
        "required": ["user_id"],
    }

    async def execute(self, **kwargs) -> ToolResult:
        user_id = kwargs.get("user_id")
        days = int(kwargs.get("days", 7))  # 默认分析最近7天

        try:
            db = get_mongo_database()
            goals_collection = db["learning_goals"]
            records_collection = db["learning_records"]

            # 获取用户学习目标
            user_goal = goals_collection.find_one({"userId": user_id})

            if not user_goal:
                return ToolResult(output=f"未找到用户 {user_id} 的学习目标")

            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 获取用户学习记录
            records_query = {
                "userId": user_id,
                "date": {"$gte": start_date, "$lte": end_date}
            }

            learn_records = list(records_collection.find({
                **records_query,
                "type": "learn"
            }))

            review_records = list(records_collection.find({
                **records_query,
                "type": "review"
            }))

            # 分析每天学习情况
            daily_stats = {}
            for i in range(days):
                date = (end_date - timedelta(days=i)).strftime("%Y-%m-%d")
                daily_stats[date] = {
                    "new_words": 0,
                    "review_words": 0
                }

            # 统计新学习的单词
            for record in learn_records:
                record_date = record.get("date")
                if isinstance(record_date, datetime):
                    date_str = record_date.strftime("%Y-%m-%d")
                    if date_str in daily_stats:
                        daily_stats[date_str]["new_words"] += record.get("count", 0)

            # 统计复习的单词
            for record in review_records:
                record_date = record.get("date")
                if isinstance(record_date, datetime):
                    date_str = record_date.strftime("%Y-%m-%d")
                    if date_str in daily_stats:
                        daily_stats[date_str]["review_words"] += record.get("count", 0)

            # 计算目标完成情况
            daily_new_goal = user_goal.get("dailyNewWordsGoal", 0)
            daily_review_goal = user_goal.get("dailyReviewWordsGoal", 0)

            total_new_words = sum(day["new_words"] for day in daily_stats.values())
            total_review_words = sum(day["review_words"] for day in daily_stats.values())

            total_new_goal = daily_new_goal * days
            total_review_goal = daily_review_goal * days

            new_completion_rate = (total_new_words / total_new_goal * 100) if total_new_goal > 0 else 0
            review_completion_rate = (total_review_words / total_review_goal * 100) if total_review_goal > 0 else 0

            # 格式化结果
            result = f"用户 {user_id} 的学习目标与完成情况分析 (最近{days}天):\n\n"

            result += "学习目标:\n"
            result += f"- 每日新单词目标: {daily_new_goal} 个\n"
            result += f"- 每日复习单词目标: {daily_review_goal} 个\n\n"

            result += "总体完成情况:\n"
            result += f"- 新单词学习: {total_new_words}/{total_new_goal} ({new_completion_rate:.1f}%)\n"
            result += f"- 单词复习: {total_review_words}/{total_review_goal} ({review_completion_rate:.1f}%)\n\n"

            result += "每日详情:\n"
            for date, stats in sorted(daily_stats.items(), reverse=True):
                new_words = stats["new_words"]
                review_words = stats["review_words"]

                new_completion = (new_words / daily_new_goal * 100) if daily_new_goal > 0 else 0
                review_completion = (review_words / daily_review_goal * 100) if daily_review_goal > 0 else 0

                result += f"- {date}: 新词 {new_words}/{daily_new_goal} ({new_completion:.1f}%), "
                result += f"复习 {review_words}/{daily_review_goal} ({review_completion:.1f}%)\n"

            return ToolResult(output=result)
        except Exception as e:
            raise ToolError(str(e))


class WordbookAnalysisTool(BaseTool):
    name: str = "wordbook_analysis"
    description: str = "分析词书内容和使用情况"

    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "wordbook_id": {
                "type": "string",
                "description": "词书ID"
            },
            "is_system": {
                "type": "boolean",
                "description": "是否为系统词书"
            }
        },
        "required": ["wordbook_id"],
    }

    async def execute(self, **kwargs) -> ToolResult:
        wordbook_id = kwargs.get("wordbook_id")
        is_system = kwargs.get("is_system", False)

        try:
            db = get_mongo_database()
            collection_name = "system_wordbooks" if is_system else "user_wordbooks"
            wordbook_collection = db[collection_name]
            words_collection = db["words"]

            # 获取词书信息
            query = {"_id": {"$oid": wordbook_id}}
            wordbook = wordbook_collection.find_one(query)

            if not wordbook:
                return ToolResult(output=f"未找到ID为 {wordbook_id} 的{('系统' if is_system else '用户')}词书")

            # 基本信息
            book_name = wordbook.get("bookName", "未命名词书")
            description = wordbook.get("description", "无描述")
            language = wordbook.get("language", "未知语言")

            result = f"词书分析: {book_name}\n"
            result += f"描述: {description}\n"
            result += f"语言: {language}\n\n"

            # 获取词书中的单词
            words_list = wordbook.get("words", [])
            word_count = len(words_list)

            result += f"单词数量: {word_count}\n\n"

            # 对于系统词书，单词直接嵌入在文档中
            if is_system:
                embedded_words = words_list

                # 分析难度分布
                difficulty_counts = {}
                for word_info in embedded_words:
                    difficulty = word_info.get("difficulty", "unknown")
                    if difficulty in difficulty_counts:
                        difficulty_counts[difficulty] += 1
                    else:
                        difficulty_counts[difficulty] = 1

                result += "难度分布:\n"
                for difficulty, count in sorted(difficulty_counts.items()):
                    result += f"- 级别 {difficulty}: {count} 个单词 ({count/word_count*100:.1f}%)\n"

                # 词性分布
                pos_counts = {}
                for word_info in embedded_words:
                    pos_list = word_info.get("partOfSpeechList", [])
                    for pos in pos_list:
                        if pos in pos_counts:
                            pos_counts[pos] += 1
                        else:
                            pos_counts[pos] = 1

                result += "\n词性分布:\n"
                for pos, count in sorted(pos_counts.items(), key=lambda x: x[1], reverse=True):
                    result += f"- {pos}: {count} 个单词 ({count/word_count*100:.1f}%)\n"

                # 标签分布
                tag_counts = {}
                for word_info in embedded_words:
                    tags = word_info.get("tags", [])
                    for tag in tags:
                        if tag in tag_counts:
                            tag_counts[tag] += 1
                        else:
                            tag_counts[tag] = 1

                result += "\n标签分布 (前5个):\n"
                for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                    result += f"- {tag}: {count} 个单词 ({count/word_count*100:.1f}%)\n"

                # 单词样例
                result += f"\n单词样例 (前5个):\n"
                for i, word_info in enumerate(embedded_words[:5]):
                    result += f"{i+1}. {word_info.get('word', 'unknown')}"
                    if "partOfSpeechList" in word_info and word_info["partOfSpeechList"]:
                        result += f" ({word_info['partOfSpeechList'][0] if isinstance(word_info['partOfSpeechList'][0], str) else '复合词性'})"
                    result += "\n"

            # 对于用户词书，单词存储为ID引用
            else:
                # 获取词书中的单词详情
                word_ids = []
                for word_id in words_list:
                    # 处理两种可能的ID格式
                    if isinstance(word_id, dict) and "$oid" in word_id:
                        word_ids.append({"_id": {"$oid": word_id["$oid"]}})
                    else:
                        word_ids.append({"_id": {"$oid": word_id}})

                if not word_ids:
                    result += "词书中没有单词\n"
                    return ToolResult(output=result)

                # 查询单词详情
                word_details = []
                for word_query in word_ids:
                    word_doc = words_collection.find_one(word_query)
                    if word_doc:
                        word_details.append(word_doc)

                if not word_details:
                    result += "未能找到词书中的单词详情\n"
                    return ToolResult(output=result)

                # 分析难度分布
                difficulty_counts = {}
                for word in word_details:
                    difficulty = word.get("difficulty", "unknown")
                    if difficulty in difficulty_counts:
                        difficulty_counts[difficulty] += 1
                    else:
                        difficulty_counts[difficulty] = 1

                result += "难度分布:\n"
                for difficulty, count in sorted(difficulty_counts.items()):
                    result += f"- 级别 {difficulty}: {count} 个单词 ({count/len(word_details)*100:.1f}%)\n"

                # 标签分布
                tag_counts = {}
                for word in word_details:
                    tags = word.get("tags", [])
                    for tag in tags:
                        if tag in tag_counts:
                            tag_counts[tag] += 1
                        else:
                            tag_counts[tag] = 1

                result += "\n标签分布 (前5个):\n"
                for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                    result += f"- {tag}: {count} 个单词 ({count/len(word_details)*100:.1f}%)\n"

                # 单词列表
                result += f"\n单词列表 (前5个):\n"
                for i, word in enumerate(word_details[:5]):
                    result += f"{i+1}. {word.get('word', 'unknown')}"
                    if "partOfSpeechList" in word and word["partOfSpeechList"]:
                        first_pos = word["partOfSpeechList"][0]
                        if "definitions" in first_pos and first_pos["definitions"]:
                            result += f" - {first_pos['definitions'][0]}"
                    result += "\n"

            return ToolResult(output=result)
        except Exception as e:
            raise ToolError(str(e))


class LearningVisualizationTool(BaseTool):
    name: str = "learning_visualization"
    description: str = "生成学习数据可视化图表，包括学习进度、单词掌握情况等"

    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "用户ID"
            },
            "chart_type": {
                "type": "string",
                "description": "图表类型，支持 'progress_trend', 'proficiency_distribution', 'difficulty_distribution', 'daily_activity'"
            },
            "days": {
                "type": "integer",
                "description": "分析最近多少天的数据"
            }
        },
        "required": ["user_id", "chart_type"],
    }

    async def execute(self, **kwargs) -> ToolResult:
        user_id = kwargs.get("user_id")
        chart_type = kwargs.get("chart_type")
        days = int(kwargs.get("days", 30))  # 默认30天

        try:
            db = get_mongo_database()
            progress_collection = db["word_learning_progress"]
            records_collection = db["learning_records"]
            goals_collection = db["learning_goals"]

            # 创建输出目录
            output_dir = "outputs"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 生成图表文件名
            chart_filename = f"{user_id}_{chart_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            chart_path = os.path.join(output_dir, chart_filename)

            plt.figure(figsize=(10, 6))

            # 根据图表类型生成不同的可视化
            if chart_type == "progress_trend":
                # 学习进度趋势
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)

                # 查询时间范围内的学习记录
                records_query = {
                    "userId": user_id,
                    "date": {"$gte": start_date, "$lte": end_date}
                }

               # 按日期分组统计学习记录
                pipeline = [
                    {"$match": records_query},
                    {"$group": {
                        "_id": {
                            "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$date"}},
                            "type": "$type"
                        },
                        "count": {"$sum": "$count"}
                    }},
                    {"$sort": {"_id.date": 1}}
                ]
                daily_records = list(records_collection.aggregate(pipeline))

                # 准备数据
                dates = []
                new_words_data = []
                review_words_data = []

                date_format = "%Y-%m-%d"
                current_date = start_date
                while current_date <= end_date:
                    date_str = current_date.strftime(date_format)
                    dates.append(date_str)

                    # 初始化该日期的数据
                    new_words = 0
                    review_words = 0

                    # 查找该日期的记录
                    for record in daily_records:
                        if record["_id"]["date"] == date_str:
                            if record["_id"]["type"] == "learn":
                                new_words = record["count"]
                            elif record["_id"]["type"] == "review":
                                review_words = record["count"]

                    new_words_data.append(new_words)
                    review_words_data.append(review_words)

                    # 移到下一天
                    current_date += timedelta(days=1)

                # 获取用户目标
                user_goal = goals_collection.find_one({"userId": user_id})
                daily_new_goal = user_goal.get("dailyNewWordsGoal", 0) if user_goal else 0
                daily_review_goal = user_goal.get("dailyReviewWordsGoal", 0) if user_goal else 0

                # 创建趋势图
                x = range(len(dates))
                plt.bar(x, new_words_data, width=0.4, label='新单词', color='blue', alpha=0.6)
                plt.bar([i + 0.4 for i in x], review_words_data, width=0.4, label='复习单词', color='green', alpha=0.6)

                # 添加目标线
                if daily_new_goal > 0:
                    plt.axhline(y=daily_new_goal, linestyle='--', color='blue', alpha=0.8, label='新单词目标')
                if daily_review_goal > 0:
                    plt.axhline(y=daily_review_goal, linestyle='--', color='green', alpha=0.8, label='复习目标')

                plt.xlabel('日期')
                plt.ylabel('单词数量')
                plt.title(f'用户学习进度趋势 (最近{days}天)')
                plt.xticks([i + 0.2 for i in x], [d.split('-')[1] + '-' + d.split('-')[2] for d in dates], rotation=45)
                plt.legend()
                plt.tight_layout()

            elif chart_type == "proficiency_distribution":
                # 熟练度分布
                progress_query = {"userId": user_id}
                progress_records = list(progress_collection.find(progress_query))

                if not progress_records:
                    return ToolResult(output=f"未找到用户 {user_id} 的学习进度记录")

                # 计算熟练度分布
                proficiency_ranges = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
                proficiency_labels = ['初学 (0-0.2)', '学习中 (0.2-0.4)', '掌握 (0.4-0.6)',
                                     '熟练 (0.6-0.8)', '精通 (0.8-1.0)']
                proficiency_counts = [0] * (len(proficiency_ranges) - 1)

                for record in progress_records:
                    prof = record.get("proficiency", 0)
                    for i in range(len(proficiency_ranges) - 1):
                        if proficiency_ranges[i] <= prof < proficiency_ranges[i+1]:
                            proficiency_counts[i] += 1
                            break

                # 创建饼图
                plt.pie(proficiency_counts, labels=proficiency_labels, autopct='%1.1f%%',
                       startangle=90, shadow=False)
                plt.axis('equal')  # 保持饼图为圆形
                plt.title(f'单词熟练度分布 (总计{len(progress_records)}个单词)')

            elif chart_type == "difficulty_distribution":
                # 难度分布
                # 获取用户正在学习的单词ID
                progress_query = {"userId": user_id}
                progress_records = list(progress_collection.find(progress_query))

                if not progress_records:
                    return ToolResult(output=f"未找到用户 {user_id} 的学习进度记录")

                # 获取单词ID
                word_ids = []
                for record in progress_records:
                    word_id = record.get("wordId", {}).get("$oid")
                    if word_id:
                        word_ids.append({"_id": {"$oid": word_id}})

                # 获取单词详情
                words_collection = db["words"]
                words = []
                for word_query in word_ids:
                    word = words_collection.find_one(word_query)
                    if word:
                        words.append(word)

                # 分析难度分布
                difficulty_counts = {}
                for word in words:
                    difficulty = word.get("difficulty", "unknown")
                    if difficulty in difficulty_counts:
                        difficulty_counts[difficulty] += 1
                    else:
                        difficulty_counts[difficulty] = 1

                # 创建柱状图
                difficulties = list(difficulty_counts.keys())
                counts = list(difficulty_counts.values())

                # 对难度级别排序
                try:
                    # 尝试按照数字排序
                    difficulty_items = [(int(k) if isinstance(k, (int, str)) and k.isdigit() else k, v)
                                      for k, v in difficulty_counts.items()]
                    difficulty_items.sort()
                    difficulties = [str(k) for k, v in difficulty_items]
                    counts = [v for k, v in difficulty_items]
                except:
                    # 如果失败，则按照原始顺序
                    pass

                plt.bar(difficulties, counts, color='skyblue')
                plt.xlabel('难度级别')
                plt.ylabel('单词数量')
                plt.title('单词难度分布')

            elif chart_type == "daily_activity":
                # 每日学习活动
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)

                # 查询时间范围内的学习记录
                records_query = {
                    "userId": user_id,
                    "date": {"$gte": start_date, "$lte": end_date}
                }

                learn_records = list(records_collection.find({
                    **records_query,
                    "type": "learn"
                }))

                review_records = list(records_collection.find({
                    **records_query,
                    "type": "review"
                }))

                # 按小时统计活动
                hourly_activity = {i: {"learn": 0, "review": 0} for i in range(24)}

                # 统计学习活动
                for record in learn_records + review_records:
                    record_date = record.get("date")
                    if isinstance(record_date, datetime):
                        hour = record_date.hour
                        record_type = record.get("type")
                        if record_type in ["learn", "review"]:
                            hourly_activity[hour][record_type] += record.get("count", 0)

                # 准备数据
                hours = list(range(24))
                learn_data = [hourly_activity[h]["learn"] for h in hours]
                review_data = [hourly_activity[h]["review"] for h in hours]

                # 创建堆叠柱状图
                plt.bar(hours, learn_data, color='blue', alpha=0.6, label='新单词学习')
                plt.bar(hours, review_data, bottom=learn_data, color='green', alpha=0.6, label='复习')

                plt.xlabel('小时 (0-23)')
                plt.ylabel('单词数量')
                plt.title(f'每日学习活动分布 (最近{days}天)')
                plt.xticks(hours)
                plt.legend()

            else:
                return ToolResult(output=f"不支持的图表类型: {chart_type}")

            # 保存图表
            plt.savefig(chart_path)
            plt.close()

            return ToolResult(
                output=f"可视化图表已生成: {chart_path}\n"
                      f"图表类型: {chart_type}\n"
                      f"用户ID: {user_id}\n"
                      f"时间范围: 最近{days}天"
            )
        except Exception as e:
            raise ToolError(str(e))


async def cleanup_mongo_connections():
    """清理MongoDB连接"""
    # 这里可以添加清理逻辑，比如关闭连接池等
    pass


class BiAnalysisTools:
    """商务智能分析工具集合"""

    @staticmethod
    def get_tools() -> List[BaseTool]:
        """获取所有BI分析工具"""
        return [
            CollectionBasicInfoTool(),
            WordStatisticsTool(),
            LearningProgressAnalysisTool(),
            UserLearningGoalsTool(),
            WordbookAnalysisTool(),
            LearningVisualizationTool()
        ]

    @staticmethod
    async def cleanup():
        """清理资源"""
        await cleanup_mongo_connections()
