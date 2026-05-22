"""基金分析师节点：基金经理分析师、持仓分析师、风险分析师"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool

from tradingagents.dataflows.fund_data import (
    get_fund_basic_info,
    get_fund_performance,
    get_fund_risk_metrics,
    get_fund_holdings_or_index,
    get_fund_nav_history_summary,
)
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


# ── 工具定义（供 LLM bind_tools 使用）──────────────────────────────────────

@tool
def tool_get_fund_basic_info(code: str) -> str:
    """获取基金基础信息：名称、类型、规模、基金经理、投资策略、业绩比较基准"""
    return get_fund_basic_info(code)


@tool
def tool_get_fund_performance(code: str) -> str:
    """获取基金历史业绩：各年度收益率、最大回撤、同类排名、夏普比率"""
    return get_fund_performance(code)


@tool
def tool_get_fund_risk_metrics(code: str) -> str:
    """获取基金风险指标：同类排名走势、近期净值摘要、波动率"""
    return get_fund_risk_metrics(code)


@tool
def tool_get_fund_holdings(code: str, fund_type: str = "") -> str:
    """获取基金持仓：主动型返回重仓股，QDII/指数型返回资产配置和跟踪指数"""
    return get_fund_holdings_or_index(code, fund_type)


@tool
def tool_get_fund_nav_summary(code: str) -> str:
    """获取基金净值历史摘要：最新净值、区间最高最低、近1年收益率"""
    return get_fund_nav_history_summary(code)


# ── 分析师节点工厂 ──────────────────────────────────────────────────────────

def create_fund_manager_analyst(llm):
    """基金经理分析师：评价基金经理的管理能力和投资风格"""

    def node(state):
        code = state["company_of_interest"]
        trade_date = state["trade_date"]

        tools = [tool_get_fund_basic_info, tool_get_fund_performance]

        system_message = (
            "你是一位专业的基金研究员，专注于评价基金经理的管理能力。"
            "请使用工具获取基金的基础信息和历史业绩数据，然后从以下维度进行分析：\n"
            "1. 基金经理背景和管理年限\n"
            "2. 历史业绩：各年度收益率、与同类基金的比较\n"
            "3. 风险控制能力：最大回撤控制\n"
            "4. 投资风格一致性：是否与基金合同描述一致\n"
            "5. 综合评价：基金经理是否值得信赖\n\n"
            "请先调用工具获取数据，再给出详细分析报告。"
            f"当前分析日期：{trade_date}，基金代码：{code}。"
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", "{system_message}\n你可以使用的工具：{tool_names}"),
            MessagesPlaceholder(variable_name="messages"),
        ])
        prompt = prompt.partial(
            system_message=system_message,
            tool_names=", ".join([t.name for t in tools]),
        )

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = result.content if not result.tool_calls else ""
        return {"messages": [result], "fund_manager_report": report}

    return node


def create_fund_holdings_analyst(llm):
    """持仓分析师：分析基金持仓质量或跟踪指数"""

    def node(state):
        code = state["company_of_interest"]
        trade_date = state["trade_date"]
        # 从 fund_manager_report 中提取基金类型（如果已有）
        fund_type = state.get("fund_type", "")

        tools = [tool_get_fund_holdings, tool_get_fund_nav_summary, tool_get_fund_basic_info]

        system_message = (
            "你是一位专业的基金持仓分析师。"
            "请使用工具获取基金持仓数据，然后分析：\n"
            "1. 对于主动型基金：分析前十大重仓股的质量、行业集中度、持仓变化\n"
            "2. 对于 QDII/指数型基金：分析跟踪指数的质量、资产配置合理性、净值走势\n"
            "3. 持仓风险：集中度风险、行业风险\n"
            "4. 综合评价：持仓是否符合基金定位\n\n"
            "请先调用工具获取数据，再给出详细分析报告。"
            f"当前分析日期：{trade_date}，基金代码：{code}，基金类型：{fund_type or '待确认'}。"
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", "{system_message}\n你可以使用的工具：{tool_names}"),
            MessagesPlaceholder(variable_name="messages"),
        ])
        prompt = prompt.partial(
            system_message=system_message,
            tool_names=", ".join([t.name for t in tools]),
        )

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = result.content if not result.tool_calls else ""
        return {"messages": [result], "fund_holdings_report": report}

    return node


def create_fund_risk_analyst(llm):
    """风险分析师：评估基金的风险水平"""

    def node(state):
        code = state["company_of_interest"]
        trade_date = state["trade_date"]

        tools = [tool_get_fund_risk_metrics, tool_get_fund_performance, tool_get_fund_nav_summary]

        system_message = (
            "你是一位专业的基金风险分析师。"
            "请使用工具获取基金风险数据，然后分析：\n"
            "1. 波动率水平：年化波动率是否在合理范围\n"
            "2. 回撤控制：历史最大回撤、近期回撤情况\n"
            "3. 风险调整收益：夏普比率是否优秀\n"
            "4. 同类排名：在同类基金中的风险收益表现\n"
            "5. 当前风险评估：当前市场环境下的风险水平\n\n"
            "请先调用工具获取数据，再给出详细风险评估报告。"
            f"当前分析日期：{trade_date}，基金代码：{code}。"
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", "{system_message}\n你可以使用的工具：{tool_names}"),
            MessagesPlaceholder(variable_name="messages"),
        ])
        prompt = prompt.partial(
            system_message=system_message,
            tool_names=", ".join([t.name for t in tools]),
        )

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = result.content if not result.tool_calls else ""
        return {"messages": [result], "fund_risk_report": report}

    return node
