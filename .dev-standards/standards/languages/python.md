# Python Guidelines & Standards

Python 코드는 class와 pattern을 많이 사용하는 코드가 아니라 읽는 순서가 자연스럽고,
표준 protocol과 iterator, context manager를 활용하며, runtime 경계를 명확히 검증하는
코드여야 합니다. 동적 특성을 방치하지 않고 type hint로 협업 계약을 보강합니다.

## 1. Python다운 기본 원칙

- `requires-python`, runtime 고정 설정과 CI의 최소 지원 Python 버전을 확인합니다.
  해당 버전의 공식 문법·typing API를 기준으로 작성하고 Ruff/Pyright의 target도 맞춥니다.
- 아래 `dataclass(slots=True)` 예시는 Python 3.10 이상을 전제로 합니다. 새 type hint와
  annotation 처리 방식은 지원 버전에서의 import/runtime 동작까지 확인합니다. type checker가
  통과했다는 이유만으로 실행 호환성을 보장하지 않습니다.

- 단순한 동작은 module-level function으로 시작하고 공유 상태와 불변식이 실제로 있을 때
  class를 도입합니다.
- public API와 I/O 경계는 type hint를 명시하되 local variable의 자명한 타입까지
  반복하지 않습니다.
- duck typing을 유지하면서 정적 계약이 필요하면 상속 전용 base class보다 `Protocol`을
  우선 검토합니다.
- truthiness는 빈 collection 허용처럼 의미가 맞을 때 사용하고 `None`, `0`, 빈 문자열을
  구분해야 하는 계약에서는 명시적으로 비교합니다.
- module import가 네트워크 연결, thread 시작이나 설정 변경 같은 side effect를 만들지
  않게 합니다.

## 2. 데이터와 API 모델링

- 단순 value data에는 `dataclass`, 닫힌 상수 집합에는 `Enum`, dictionary shape 계약에는
  `TypedDict`를 사용합니다. 모든 domain 객체를 dictionary나 범용 model 하나로 전달하지
  않습니다.
- `frozen=True`는 실제 value semantics가 필요할 때 사용합니다. field가 mutable object를
  가리키면 frozen dataclass만으로 깊은 불변성이 생기지 않습니다.
- mutable default argument를 사용하지 않습니다. dataclass collection field에는
  `default_factory`를 사용합니다.
- 외부 payload는 parsing library 또는 명시적 parser로 경계에서 검증합니다. 특정
  validation library는 프로젝트가 이미 채택했을 때만 사용합니다.
- `assert`는 내부 불변식과 debugging 확인에만 사용합니다. 최적화 실행에서 제거될 수
  있으므로 외부 입력과 domain 규칙은 명시적인 조건 검사와 예외로 검증합니다.

```python
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Order:
    order_id: int
    total: int
    is_active: bool


class OrderRepository(Protocol):
    def find(self, order_id: int) -> Order | None: ...
```

## 3. 제어 흐름과 collection

- “허락을 구하기보다 용서를 구한다”는 EAFP를 좁은 예외 범위에서 사용합니다. 호출한
  함수 내부의 같은 예외까지 잘못 잡을 수 있는 넓은 `try` 블록은 피합니다.
- comprehension은 한 번의 간단한 filter/transform에 사용합니다. 중첩 분기, side effect,
  여러 단계 변환은 명시적인 loop나 generator function으로 분리합니다.
- 큰 데이터를 모두 materialize하지 않아도 되면 iterator/generator로 소비 시점에
  처리합니다. 반복 사용이 필요한 iterator를 실수로 한 번 소비하지 않게 계약을 정합니다.
- keyword-only argument와 이름 있는 parameter로 boolean flag와 동일 타입 인자의 의미를
  드러냅니다.
- `mapping.get(key)`는 key 부재와 기본값이 같은 의미일 때 사용합니다. 저장된 `None`과
  부재를 구분해야 하면 `key in mapping`을 사용하고, 부재가 예외적인 경우에는 좁은
  범위에서 `mapping[key]`의 `KeyError`를 처리합니다.
- `getattr(value, name, default)`로 오타와 잘못된 객체 shape를 숨기지 않습니다. 동적
  attribute가 실제 protocol인 경계에서만 사용하고 일반 model은 명시적 attribute와
  type hint를 유지합니다.

```python
from collections.abc import Iterable, Iterator


def active_order_ids(orders: Iterable[Order]) -> Iterator[int]:
    for order in orders:
        if order.is_active:
            yield order.order_id
```

EAFP는 모든 검사를 예외로 바꾸라는 뜻이 아닙니다. 경쟁 상태를 피하거나 해당 operation의
실패를 직접 처리할 때 적합하고, 값 상태 자체를 분기하는 편이 명확하면 명시적 조건을
사용합니다.

## 4. 예외와 자원 관리

- 잡을 수 있고 처리할 수 있는 구체적인 예외만 포착합니다. process 경계의 로깅 외에는
  `except Exception`으로 실패를 빈 값으로 바꾸지 않습니다.
- domain 의미로 변환할 때 `raise DomainError(...) from cause`로 traceback chain을
  보존합니다. 현재 예외를 그대로 전파할 때는 인자 없는 `raise`를 사용합니다.
- 파일, lock, transaction과 session은 `with` 또는 `async with`로 소유권과 종료 시점을
  표현합니다.
- cleanup 자체가 실패할 수 있으면 원래 예외를 가리거나 무시하지 않도록 정책을
  테스트합니다.

```python
try:
    return repository.find(order_id)
except DatabaseUnavailableError as cause:
    raise OrderLookupError(f"failed to load order {order_id}") from cause
```

## 5. Async와 동시성

- coroutine을 호출하면 반드시 await하거나 명시적으로 task lifecycle을 소유합니다.
- event loop 안에서 blocking I/O와 CPU 집약 작업을 직접 실행하지 않습니다.
- background task에는 종료, cancellation, 오류 관찰 경로를 둡니다.
- thread/process/asyncio 선택은 I/O 대기와 CPU 작업 특성을 기준으로 하며 속도 개선은
  측정합니다.

## 6. Docstring과 주석

- 공개 module, class와 function은 PEP 257 형식의 요약 문장과 필요한 계약을 기록합니다.
- 저장소가 Google, NumPy 또는 Sphinx 스타일 중 하나를 선택하면 문서 전체에서
  일관되게 사용합니다. 기본 템플릿은 Google style입니다.
- type hint를 docstring에 반복하지 않고 단위, 허용 범위, 반환 의미, side effect와
  예외 조건을 설명합니다.

```python
def load_order(order_id: int) -> Order:
    """현재 tenant에서 볼 수 있는 주문을 조회합니다.

    Args:
        order_id: 양수 주문 식별자.

    Raises:
        OrderNotFoundError: 주문이 없거나 접근할 수 없는 경우.
    """
    raise NotImplementedError
```

## 7. 테스트와 품질 게이트

- public behavior, 경계값, 예외 chain과 자원 정리를 pytest로 검증합니다.
- fixture는 범위를 작게 유지하고 autouse fixture로 숨은 전역 상태를 만들지 않습니다.
- network, clock, random은 경계에서 대체 가능하게 만들고 test 내부 sleep에 의존하지
  않습니다.

```sh
uv run --frozen pytest
ruff check .
ruff format --check .
pyright
```

시작점은 `templates/mise/python/`, `templates/ruff/`, `templates/pyright/`에 있습니다.

## 8. 다른 언어 습관을 옮기지 않는다

- Java식 getter/setter, interface마다 ABC, 한 method뿐인 service class를 기계적으로
  만들지 않습니다.
- type hint를 runtime validation으로 착각하거나 `Any`로 type checker만 통과시키지
  않습니다.
- 한 줄 comprehension과 decorator가 길고 명시적인 코드보다 언제나 Python답다고
  간주하지 않습니다.

참고: [PEP 8](https://peps.python.org/pep-0008/),
[PEP 257](https://peps.python.org/pep-0257/),
[typing.Protocol](https://docs.python.org/3/library/typing.html#typing.Protocol),
[contextlib](https://docs.python.org/3/library/contextlib.html),
[assert statement](https://docs.python.org/3/reference/simple_stmts.html#the-assert-statement)

버전별 문법 참고: [Python 3.10 변경 사항](https://docs.python.org/3.10/whatsnew/3.10.html)
