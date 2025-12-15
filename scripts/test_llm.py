#!/usr/bin/env python3
"""Test LLM client with different providers."""

import os
import sys

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from offer_sherlock.llm import LLMClient, LLMProvider


def test_qwen():
    """Test Qwen (DashScope) API."""
    print("Testing Qwen API...")
    
    client = LLMClient(provider=LLMProvider.QWEN)
    print(f"Client: {client}")
    
    response = client.chat(
        "你好！请用一句话介绍一下你自己。",
        system_prompt="你是一个友好的AI助手。"
    )
    print(f"Response: {response}")
    return True


def test_structured_output():
    """Test structured output with Qwen."""
    from pydantic import BaseModel, Field
    
    print("\nTesting structured output...")
    
    class JobInfo(BaseModel):
        """Simple job info for testing."""
        company: str = Field(description="公司名称")
        position: str = Field(description="职位名称")
        salary: str = Field(description="薪资范围")
    
    client = LLMClient(provider=LLMProvider.QWEN)
    
    result = client.chat_structured(
        "从以下信息中提取：字节跳动招聘后端开发工程师，薪资30-50K",
        output_schema=JobInfo,
        system_prompt="你是一个数据提取助手，请从文本中提取结构化信息。"
    )
    
    print(f"Extracted: {result}")
    print(f"  Company: {result.company}")
    print(f"  Position: {result.position}")
    print(f"  Salary: {result.salary}")
    return True


if __name__ == "__main__":
    try:
        test_qwen()
        test_structured_output()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
