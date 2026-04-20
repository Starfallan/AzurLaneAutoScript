import json
import os

from module.logger import logger
from module.ocr.ocr import Ocr
from module.retire.dock import CARD_GRIDS, DOCK_SCROLL, Dock
from module.retire.scanner import LevelScanner
from module.handler.login import LoginHandler
from module.ui.page import page_dock

# Ship name text region at the bottom of each dock card.
# Cards are 138 × 204 px; name text appears at approximately y = 168-192.
# ⚠ These coordinates need calibration from actual screenshots if OCR results are wrong.
CARD_NAME_GRIDS = CARD_GRIDS.crop(area=(5, 168, 130, 192), name='NAME')


class FleetStats(Dock, LoginHandler):

    def run(self):
        self.ui_ensure(page_dock)
        self.dock_filter_set()          # clear all filters, show all ships
        ships = self.fleet_stats_scan_all()
        self._fleet_stats_save(ships)
        self.ui_goto_main()
        self.config.task_delay(server_update=True)

    def fleet_stats_scan_all(self):
        """Scroll dock from top to bottom, accumulating name+level per page."""
        DOCK_SCROLL.set_top(main=self)
        ships = []
        for _ in range(100):           # safety limit: ≤ 100 pages
            image = self.device.screenshot()
            ships.extend(self._fleet_stats_scan_page(image))
            if DOCK_SCROLL.at_bottom(main=self):
                break
            DOCK_SCROLL.next_page(main=self)
        logger.info(f'FleetStats: scanned {len(ships)} ship records')
        return ships

    def _fleet_stats_scan_page(self, image):
        """Scan the 14 visible ship cards: read levels then names."""
        levels = LevelScanner().scan(image)
        names = Ocr(CARD_NAME_GRIDS.buttons, lang='cnocr',
                    name='FleetStats_NameOcr').ocr(image)

        ships = []
        for name, level in zip(names, levels):
            if not level or level <= 0:      # skip empty card slots
                continue
            ships.append({'name': str(name).strip(), 'level': int(level)})
        return ships

    def _fleet_stats_save(self, ships):
        path = self.config.FleetStats_SavePath or './stats/fleet_stats.json'
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(ships, f, ensure_ascii=False, indent=2)
        logger.info(f'FleetStats: saved {len(ships)} ships → {path}')
