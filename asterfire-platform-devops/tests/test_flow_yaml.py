import unittest
from scripts.aliyun_flow import build_acr_pipeline_yaml

class TestFlowYaml(unittest.TestCase):
    def test_external_uses_hongkong_and_codeup(self):
        y = build_acr_pipeline_yaml(
            codeup_repo="https://codeup.aliyun.com/org/proteinmpnn.git",
            branch="main",
            codeup_service_connection="codeup-sc",
            acr_service_connection="acr-sc",
            registry_domain="example-registry.cn-hangzhou.cr.aliyuncs.com",
            namespace="asterfire",
            repository="proteinmpnn",
            tag="1.0.0",
            dockerfile_path="docker/Dockerfile",
            internet_required=True,
            build_container="build-steps-public-registry.cn-beijing.cr.aliyuncs.com/build-steps/alinux3:latest",
            acr_edition="enterprise",
            instance_name="cri-enterprise-demo",
        )
        self.assertIn("type: codeup", y)
        self.assertIn("group: public/cn-hongkong", y)
        self.assertIn("step: DockerBuildPushACREE", y)
        self.assertIn('dockerfilePath: "docker/Dockerfile"', y)
        self.assertIn('instance: "cri-enterprise-demo"', y)
        self.assertIn('namespace: "asterfire"', y)
        self.assertIn('dockerRegistry: "proteinmpnn"', y)
        self.assertIn('dockerTag: "1.0.0"', y)
        self.assertIn('serviceConnection: "acr-sc"', y)
        self.assertIn('region: "cn-hangzhou"', y)

    def test_no_external_uses_beijing(self):
        y = build_acr_pipeline_yaml(
            codeup_repo="repo",
            branch="main",
            codeup_service_connection="codeup-sc",
            acr_service_connection="acr-sc",
            registry_domain="registry",
            namespace="asterfire",
            repository="x",
            tag="1.0.0",
            dockerfile_path="Dockerfile",
            internet_required=False,
            build_container="container",
            acr_edition="enterprise",
            instance_name="cri-enterprise-demo",
        )
        self.assertIn("group: public/cn-beijing", y)

if __name__ == "__main__":
    unittest.main()
