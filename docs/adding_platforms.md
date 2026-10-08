# Guide: Adding New Platforms to NetEyes

Adding a new platform or channel to NetEyes requires four simple steps. Follow this guide to maintain architectural consistency.

---

## Step 1: Create the Backend Adapter

Create a backend adapter in `neteyes/backends/<platform>/<name>_backend.py`:

```python
from typing import Any, Optional, Tuple
import time
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus
from neteyes.utils.http import get_http_client

class MyPlatformBackend(BaseBackend):
    id = "myplatform_api"
    name = "MyPlatform Official API"
    priority = 10
    description = "Extracts posts and media from MyPlatform"
    backend_type = BackendType.DIRECT_API
    requires_auth = False
    dependencies = ["httpx"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        # Return HealthStatus.HEALTHY, DEGRADED, or MISSING_DEPENDENCY
        return HealthStatus.HEALTHY, "MyPlatform is online and responsive"

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        # Return the upstream command line if an agent can execute it directly
        url = kwargs.get("url")
        if action == "post" and url:
            return f'curl -sL "https://api.myplatform.com/post?url={url}"'
        return None

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        url = kwargs.get("url")
        if not url:
            return self._make_result(False, "myplatform", action, start_time, error="Missing 'url'")

        try:
            client = get_http_client(platform="myplatform")
            resp = client.get(f"https://api.myplatform.com/post?url={url}")
            resp.raise_for_status()
            data = resp.json()

            markdown_output = f"# MyPlatform Post\n\n{data.get('content')}"
            return self._make_result(
                True, "myplatform", action, start_time,
                data=data,
                markdown=markdown_output
            )
        except Exception as e:
            return self._make_result(False, "myplatform", action, start_time, error=str(e))
```

Export your backend in `neteyes/backends/<platform>/__init__.py`.

---

## Step 2: Create the Channel Declaration

Create `neteyes/channels/<platform>.py`:

```python
from typing import List
from neteyes.backends.base import BaseBackend
from neteyes.backends.myplatform import MyPlatformBackend
from neteyes.models import ActionSpec, ChannelSpec

class MyPlatformChannel:
    id = "myplatform"
    name = "MyPlatform"
    description = "Community posts and discussions from MyPlatform"
    login_walled = False
    zero_config = True

    @classmethod
    def get_spec(cls) -> ChannelSpec:
        backends = [b.get_spec() for b in cls.get_backends()]
        actions = [
            ActionSpec(
                name="post",
                description="Fetch single post and metadata",
                parameters={"url": "Post URL or identifier"},
                example_args=["https://myplatform.com/p/12345"],
            ),
        ]
        return ChannelSpec(
            id=cls.id,
            name=cls.name,
            description=cls.description,
            actions=actions,
            backends=backends,
            login_walled=cls.login_walled,
            zero_config=cls.zero_config,
        )

    @classmethod
    def get_backends(cls) -> List[BaseBackend]:
        """Ordered list of backends: Primary -> Fallbacks."""
        return [
            MyPlatformBackend(),  # Priority 10
            # Add secondary fallbacks here if available
        ]
```

---

## Step 3: Register in Channel Registry

Open `neteyes/channels/__init__.py`:

1. Import `MyPlatformChannel`
2. Add to `CHANNEL_REGISTRY`:
   ```python
   CHANNEL_REGISTRY = {
       ...
       "myplatform": MyPlatformChannel,
   }
   ```
3. Add aliases to `CHANNEL_ALIASES` if applicable (e.g. `"mp": "myplatform"`).

---

## Step 4: (Optional) Register Cookie Signatures

If the platform is login-walled, open `neteyes/auth.py` and register the critical session cookie names:

```python
PLATFORM_COOKIE_SIGNATURES = {
    ...
    "myplatform": ["session_id", "auth_token"],
}
```

---

## Step 5: Test and Verify

Run NetEyes CLI to verify your new channel:

```bash
# Verify it appears in channel list
neteyes list

# Verify doctor recognizes it
neteyes doctor

# Test capability routing
neteyes route myplatform post "https://myplatform.com/p/12345"

# Test execution
neteyes run myplatform post "https://myplatform.com/p/12345"
```
