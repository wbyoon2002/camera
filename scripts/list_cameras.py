#!/usr/bin/env python3
"""
카메라 인덱스 탐색 유틸리티 (실시간 미리보기)
---------------------------------------------
연결된 카메라를 하나씩 실시간 영상으로 보여줍니다. 화면을 보고 어느 인덱스가
USB 카메라인지 확인한 뒤, 그 번호를 cfg/capture_cfg.yaml 의 camera.index 에 넣으세요.

  python scripts/list_cameras.py            # 실시간 미리보기 (n=다음, q=종료)
  python scripts/list_cameras.py --list     # 미리보기 없이 사용 가능한 인덱스만 출력

Windows에서는 USB 카메라 인식이 더 안정적인 DirectShow 백엔드를 우선 사용합니다.
"""
import sys
import cv2

LIST_ONLY = "--list" in sys.argv
MAX_INDEX = 6

# Windows에서 USB 카메라에 더 안정적인 DirectShow를 우선 시도
BACKEND = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY


def find_cameras():
    found = []
    for idx in range(MAX_INDEX):
        cap = cv2.VideoCapture(idx, BACKEND)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                found.append((idx, w, h))
        cap.release()
    return found


def main():
    print("카메라를 탐색합니다...\n")
    cams = find_cameras()

    if not cams:
        print("사용 가능한 카메라를 찾지 못했습니다.")
        print("USB 연결 상태와, 다른 앱(줌/카메라 앱 등)이 카메라를 점유 중인지 확인하세요.")
        return

    print("사용 가능한 카메라:")
    for idx, w, h in cams:
        print(f"  - index {idx}  ({w}x{h})")
    print()

    if LIST_ONLY:
        print("→ 위 번호 중 USB 카메라를 cfg/capture_cfg.yaml 의 camera.index 에 설정하세요.")
        return

    print("각 카메라의 실시간 영상을 보여줍니다.")
    print("  [n] 다음 카메라   [q] 종료\n")

    for idx, w, h in cams:
        cap = cv2.VideoCapture(idx, BACKEND)
        if not cap.isOpened():
            continue
        win = f"Camera index {idx}"
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break
            cv2.putText(frame, f"index {idx}   [n] next  [q] quit", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.imshow(win, frame)
            key = cv2.waitKey(30) & 0xFF
            if key == ord('n'):
                break
            if key == ord('q'):
                cap.release()
                cv2.destroyAllWindows()
                print("종료합니다.")
                return
        cap.release()
        cv2.destroyWindow(win)

    cv2.destroyAllWindows()
    print("모든 카메라를 확인했습니다. USB 카메라 번호를 camera.index 에 설정하세요.")


if __name__ == "__main__":
    main()
