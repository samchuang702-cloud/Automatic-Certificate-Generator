#!/usr/bin/env python
"""
詳細測試：檔案大小限制功能
"""
import asyncio
import pytest
from fastapi import HTTPException
from app.routers.admin_excel import read_file_with_size_limit, MAX_EXCEL_FILE_SIZE


class MockUploadFile:
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.index = 0

    async def read(self, size: int = -1) -> bytes:
        if self.index >= len(self.chunks):
            return b""

        chunk = self.chunks[self.index]
        self.index += 1
        return chunk


@pytest.mark.asyncio
async def test_small_file_accepted():
    """測試：小於限制的檔案被接受"""
    # 建立模擬的小檔案
    small_content = b"small file content" * 100  # 大約 1.8KB
    mock_file = MockUploadFile([small_content])
    
    result = await read_file_with_size_limit(mock_file)
    
    assert result == small_content
    print("✅ 小檔案測試通過")

@pytest.mark.asyncio
async def test_file_at_limit_accepted():
    """測試：恰好在限制邊界的檔案被接受"""
    # 建立恰好等於限制的檔案
    limit_content = b"x" * (MAX_EXCEL_FILE_SIZE - 1)
    mock_file = MockUploadFile([limit_content])
    
    result = await read_file_with_size_limit(mock_file)
    
    assert len(result) == MAX_EXCEL_FILE_SIZE - 1
    print("✅ 邊界大小檔案測試通過")

@pytest.mark.asyncio
async def test_file_over_limit_rejected():
    """測試：超過限制的檔案被拒絕"""
    # 建立超過限制的檔案
    over_limit_content = b"x" * (MAX_EXCEL_FILE_SIZE + 1024)
    mock_file = MockUploadFile([over_limit_content])
    
    with pytest.raises(HTTPException) as exc_info:
        await read_file_with_size_limit(mock_file)
    
    assert exc_info.value.status_code == 413
    assert "超過限制" in exc_info.value.detail
    print("✅ 超大檔案被正確拒絕")

@pytest.mark.asyncio
async def test_large_file_with_multiple_chunks():
    """測試：大型檔案分多個 chunk 上傳時的檢查"""
    # 模擬分多個 chunk 上傳超大檔案
    chunk_size = 10 * 1024 * 1024  # 10MB per chunk
    chunks = [b"x" * chunk_size for _ in range(6)]  # 6 chunks = 60MB (超過 50MB 限制)
    mock_file = MockUploadFile(chunks)
    
    with pytest.raises(HTTPException) as exc_info:
        await read_file_with_size_limit(mock_file)
    
    assert exc_info.value.status_code == 413
    print("✅ 多 chunk 超大檔案檢查通過")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 檔案大小限制詳細測試")
    print("=" * 60)
    print(f"\n最大允許大小: {MAX_EXCEL_FILE_SIZE / 1024 / 1024:.1f}MB\n")
    
    # 運行異步測試
    asyncio.run(test_small_file_accepted())
    asyncio.run(test_file_at_limit_accepted())
    asyncio.run(test_file_over_limit_rejected())
    asyncio.run(test_large_file_with_multiple_chunks())
    
    print("\n" + "=" * 60)
    print("🎉 所有大小限制測試通過！")
    print("=" * 60)
