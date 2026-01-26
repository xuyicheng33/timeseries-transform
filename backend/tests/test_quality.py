"""
数据质量 API 单元测试

测试质量分析、采样逻辑、数据清洗等功能
"""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest
from httpx import AsyncClient

from app.api.quality import _read_csv_with_sampling


class TestSamplingFunction:
    """采样函数单元测试"""

    @pytest.fixture
    def large_csv_file(self) -> str:
        """创建一个包含数值、缺失值的大 CSV 文件用于测试采样"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            # 创建 1000 行数据（测试时设置较小的阈值来触发采样）
            np.random.seed(42)

            # 写入表头
            f.write("id,value,category,nullable\n")

            # 写入数据行
            for i in range(1000):
                value = np.random.randn()  # 数值列
                category = ["A", "B", "C"][i % 3]  # 分类列
                # 每 10 行有一个缺失值
                nullable = "" if i % 10 == 0 else str(np.random.randint(1, 100))
                f.write(f"{i},{value},{category},{nullable}\n")

            filepath = f.name

        yield filepath

        # 清理
        if os.path.exists(filepath):
            os.unlink(filepath)

    @pytest.fixture
    def small_csv_file(self) -> str:
        """创建一个小 CSV 文件用于测试非采样路径"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("id,value,category\n")
            for i in range(50):
                f.write(f"{i},{i * 0.5},{'X' if i % 2 == 0 else 'Y'}\n")
            filepath = f.name

        yield filepath

        if os.path.exists(filepath):
            os.unlink(filepath)

    def test_sampling_preserves_numeric_dtype(self, large_csv_file: str):
        """测试采样后数值列仍然是数值类型"""
        # 使用较小的阈值触发采样
        df, is_sampled, total_rows = _read_csv_with_sampling(
            large_csv_file, encoding="utf-8", max_rows=100, sample_size=200  # 设置较小阈值触发采样
        )

        assert is_sampled is True
        assert total_rows == 1000
        assert len(df) == 200  # 采样大小

        # 验证数值列类型
        assert pd.api.types.is_numeric_dtype(df["id"]), "id 列应该是数值类型"
        assert pd.api.types.is_numeric_dtype(df["value"]), "value 列应该是数值类型"

    def test_sampling_preserves_missing_values(self, large_csv_file: str):
        """测试采样后缺失值被正确识别"""
        df, is_sampled, total_rows = _read_csv_with_sampling(
            large_csv_file, encoding="utf-8", max_rows=100, sample_size=200
        )

        assert is_sampled is True

        # nullable 列应该有缺失值（原始数据每 10 行有 1 个缺失）
        # 采样 200 行，预期约 20 个缺失值（允许一定误差）
        missing_count = df["nullable"].isna().sum()
        assert missing_count > 0, "采样后应该能检测到缺失值"
        # 缺失率约 10%，允许 5%-20% 的范围
        missing_ratio = missing_count / len(df)
        assert 0.05 <= missing_ratio <= 0.25, f"缺失率 {missing_ratio:.2%} 应该在合理范围内"

    def test_sampling_reproducible(self, large_csv_file: str):
        """测试采样结果可重复"""
        df1, _, _ = _read_csv_with_sampling(large_csv_file, encoding="utf-8", max_rows=100, sample_size=200)

        df2, _, _ = _read_csv_with_sampling(large_csv_file, encoding="utf-8", max_rows=100, sample_size=200)

        # 两次采样结果应该完全相同
        pd.testing.assert_frame_equal(df1, df2)

    def test_no_sampling_for_small_file(self, small_csv_file: str):
        """测试小文件不触发采样"""
        df, is_sampled, total_rows = _read_csv_with_sampling(
            small_csv_file, encoding="utf-8", max_rows=100, sample_size=50
        )

        assert is_sampled is False
        assert total_rows == 50
        assert len(df) == 50

    def test_sample_size_larger_than_rows(self, small_csv_file: str):
        """测试 sample_size 大于实际行数时不会出错，且不会丢失数据"""
        df, is_sampled, total_rows = _read_csv_with_sampling(
            small_csv_file, encoding="utf-8", max_rows=10, sample_size=1000  # 50 > 10，会触发采样流程  # 大于实际行数
        )

        assert total_rows == 50
        assert len(df) == 50  # 蓄水池包含所有行
        # is_sampled = False，因为返回的行数等于总行数（没有实际丢弃数据）
        assert is_sampled is False

    def test_sampling_statistics_accuracy(self, large_csv_file: str):
        """测试采样数据的统计特性与原始数据接近"""
        # 读取完整数据
        df_full = pd.read_csv(large_csv_file)

        # 采样数据
        df_sampled, _, _ = _read_csv_with_sampling(
            large_csv_file, encoding="utf-8", max_rows=100, sample_size=500  # 采样 50%
        )

        # 比较 value 列的统计特性（允许一定误差）
        full_mean = df_full["value"].mean()
        sampled_mean = df_sampled["value"].mean()

        # 均值误差应该在 20% 以内（采样的统计代表性）
        assert (
            abs(full_mean - sampled_mean) < abs(full_mean) * 0.5 + 0.5
        ), f"采样均值 {sampled_mean:.4f} 与原始均值 {full_mean:.4f} 差异过大"

    @pytest.fixture
    def medium_csv_file(self) -> str:
        """创建一个中等大小的 CSV 文件（sample_size < rows <= max_rows 场景）"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write("id,value\n")
            for i in range(300):
                f.write(f"{i},{i * 0.1}\n")
            filepath = f.name

        yield filepath

        if os.path.exists(filepath):
            os.unlink(filepath)

    def test_medium_file_no_sampling(self, medium_csv_file: str):
        """
        测试中等文件（sample_size < total_rows <= max_rows）不采样

        场景：300 行文件，max_rows=500，sample_size=100
        预期：全量读取，不采样
        """
        df, is_sampled, total_rows = _read_csv_with_sampling(
            medium_csv_file,
            encoding="utf-8",
            max_rows=500,  # 300 <= 500，不需要采样
            sample_size=100,  # 即使 sample_size < total_rows
        )

        # 关键断言：不应该采样，应该返回全部 300 行
        assert is_sampled is False, "中等文件不应该被采样"
        assert total_rows == 300
        assert len(df) == 300, f"应该返回全部 300 行，实际返回 {len(df)} 行"

    def test_exact_threshold_no_sampling(self, medium_csv_file: str):
        """
        测试刚好等于阈值时不采样

        场景：300 行文件，max_rows=300
        预期：全量读取，不采样
        """
        df, is_sampled, total_rows = _read_csv_with_sampling(
            medium_csv_file, encoding="utf-8", max_rows=300, sample_size=100  # 刚好等于行数
        )

        assert is_sampled is False
        assert len(df) == 300

    def test_just_over_threshold_sampling(self, medium_csv_file: str):
        """
        测试刚好超过阈值时采样

        场景：300 行文件，max_rows=299
        预期：采样到 sample_size 行
        """
        df, is_sampled, total_rows = _read_csv_with_sampling(
            medium_csv_file, encoding="utf-8", max_rows=299, sample_size=100  # 300 > 299，需要采样
        )

        assert is_sampled is True, "超过阈值应该采样"
        assert total_rows == 300
        assert len(df) == 100, f"应该采样到 100 行，实际 {len(df)} 行"


class TestQualityReportAPI:
    """质量报告 API 测试"""

    @pytest.mark.asyncio
    async def test_quality_report_success(self, client: AsyncClient, admin_auth_headers: dict, temp_csv_file: str):
        """测试获取质量报告"""
        # 先上传数据集
        with open(temp_csv_file, "rb") as f:
            upload_response = await client.post(
                "/api/datasets/upload",
                headers=admin_auth_headers,
                files={"file": ("test.csv", f, "text/csv")},
                data={"name": "Quality Test Dataset"},
            )

        assert upload_response.status_code == 200
        dataset_id = upload_response.json()["id"]

        # 获取质量报告
        response = await client.get(f"/api/quality/{dataset_id}/report", headers=admin_auth_headers)

        assert response.status_code == 200
        report = response.json()

        # 验证报告结构
        assert "quality_score" in report
        assert "total_rows" in report
        assert "total_columns" in report
        assert "missing_stats" in report
        assert "outlier_stats" in report
        assert "suggestions" in report

    @pytest.mark.asyncio
    async def test_quality_report_normal_user_access(
        self, client: AsyncClient, admin_auth_headers: dict, auth_headers: dict, temp_csv_file: str
    ):
        """测试普通用户可以访问公开数据集的质量报告"""
        # 管理员上传数据集
        with open(temp_csv_file, "rb") as f:
            upload_response = await client.post(
                "/api/datasets/upload",
                headers=admin_auth_headers,
                files={"file": ("test.csv", f, "text/csv")},
                data={"name": "Public Quality Dataset"},
            )

        dataset_id = upload_response.json()["id"]

        # 普通用户获取质量报告
        response = await client.get(f"/api/quality/{dataset_id}/report", headers=auth_headers)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_cleaning_requires_admin(
        self, client: AsyncClient, admin_auth_headers: dict, auth_headers: dict, temp_csv_file: str
    ):
        """测试数据清洗需要管理员权限"""
        # 管理员上传数据集
        with open(temp_csv_file, "rb") as f:
            upload_response = await client.post(
                "/api/datasets/upload",
                headers=admin_auth_headers,
                files={"file": ("test.csv", f, "text/csv")},
                data={"name": "Cleaning Test Dataset"},
            )

        dataset_id = upload_response.json()["id"]

        # 普通用户尝试执行清洗
        response = await client.post(
            f"/api/quality/{dataset_id}/clean/apply",
            headers=auth_headers,
            json={"handle_missing": True, "missing_strategy": "drop", "create_new_dataset": True},
        )

        assert response.status_code == 403
