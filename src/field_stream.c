/* A 34 x 30 tile cache for a 33 x 29 maximum visible viewport.
 * Each painting tile is preserved in ROM. Walking replaces one offscreen
 * row or column, at most 1088 character bytes plus 128 bytes of map DMA. The
 * 64 x 32 hardware map wraps vertically; character slots wrap at 34 x 30.
 * Only init/flush/animation touch VRAM, in forced blank or V-blank.
 * Preparation runs during visible-frame logic (ppu-graphics.md, Access periods). No source transfer crosses its 16KB LoROM strip.
 */
#include "ttrpg.h"
#include "worldmap.h"

u16 fieldCacheMap[2048];
u16 fieldColumn[32];
static u8 cacheX, cacheY, fxCursor;
u8 *fieldAttributes;
u8 *fieldStrips[8];
/* Eight bytes: source address/bank/pad, destination word address, size.
 * Prepared during game logic; the assembly drain does only DMA in V-blank. */
u8 fieldDma[40 * 8];
u16 fieldDmaBytes;
u16 fieldDmaOverruns;
static u8 filling;
u16 fieldPlanX, fieldPlanY, fieldPlanN, fieldPlanDX, fieldPlanDY;
u16 fieldWork[4];
void fieldQueueLine(void);

static void transfer(u8 *source, u16 destination, u16 size) {
    dmaMemory p;
    u16 n;
    if (filling) {
        dmaCopyVram(source, destination, size);
        return;
    }
    p.mem.p = source;
    n = fieldDmaBytes;
    fieldDma[n] = p.mem.c.addr & 255;
    fieldDma[n + 1] = p.mem.c.addr >> 8;
    fieldDma[n + 2] = p.mem.c.bank;
    fieldDma[n + 3] = 0x80;
    fieldDma[n + 4] = destination & 255;
    fieldDma[n + 5] = destination >> 8;
    fieldDma[n + 6] = size & 255;
    fieldDma[n + 7] = size >> 8;
    fieldDmaBytes += 8;
}

static u16 slot(u8 x, u8 y) {
    if (y >= 60) y -= 60;
    else if (y >= 30) y -= 30;
    if (x >= 34) x -= 34;
    return (u16)y * 34 + x;
}

static u16 mapIndex(u8 x, u8 y) {
    return ((u16)(y & 31) << 5) + (x & 31) + ((x & 32) ? 1024 : 0);
}

static void tile(u8 x, u8 y) {
    u16 name, offset;
    u8 *source;

    name = slot(x, y);
    source = fieldStrips[y >> 3] + ((u16)(y & 7) << 11) + ((u16)x << 5);
    transfer(source, VRAM_FIELD_GFX + (name << 4), 32);
    offset = ((u16)y << 7) + ((u16)x << 1);
    fieldCacheMap[mapIndex(x, y)] = name | ((u16)fieldAttributes[offset + 1] << 8);
}

static u8 left(void) {
    u8 x = (u16)scrollX >> 3;
    return x > 30 ? 30 : x;
}

static u8 top(void) {
    u8 y = (u16)scrollY >> 3;
    return y > 34 ? 34 : y;
}

void fieldStreamInit(void) {
    u8 x, y;
    u16 i;

    fieldAttributes = areaMap(curArea);
    filling = 1;
    fieldDmaBytes = 0;
    fieldDmaOverruns = 0;
    for (x = 0; x < 8; x++) fieldStrips[x] = areaStrip(curArea, x);
    cacheX = left();
    cacheY = top();
    fxCursor = 0;
    for (i = 0; i < 2048; i++) fieldCacheMap[i] = 0;
    for (y = cacheY; y < cacheY + 30; y++)
        for (x = cacheX; x < cacheX + 34; x++) tile(x, y);
    dmaCopyVram((u8 *)fieldCacheMap, VRAM_FIELD_MAP, 4096);
    filling = 0;
}

void fieldStreamPrepare(void) {
    u8 nx, ny, edge;
    u16 offset;

    nx = left();
    ny = top();
    if (nx != cacheX) {
        edge = nx > cacheX ? nx + 33 : nx;
        fieldPlanX = edge; fieldPlanY = cacheY; fieldPlanN = 30;
        fieldPlanDX = 0; fieldPlanDY = 1; fieldQueueLine();
        offset = ((edge & 32) ? 1024 : 0) + (edge & 31);
        transfer((u8 *)fieldColumn, VRAM_FIELD_MAP + offset, 64);
        /* VRAM increment 32 writes a column without copying its 2KB map. */
        fieldDma[fieldDmaBytes - 5] = 0x81;
        cacheX = nx;
    }
    if (ny != cacheY) {
        edge = ny > cacheY ? ny + 29 : ny;
        fieldPlanX = cacheX; fieldPlanY = edge; fieldPlanN = 34;
        fieldPlanDX = 1; fieldPlanDY = 0; fieldQueueLine();
        offset = (u16)(edge & 31) << 5;
        transfer((u8 *)(fieldCacheMap + offset), VRAM_FIELD_MAP + offset, 64);
        transfer((u8 *)(fieldCacheMap + offset + 1024), VRAM_FIELD_MAP + offset + 1024, 64);
        cacheY = ny;
    }
}

void fieldAnimate(void) {
    u8 *effect;
    u8 x, y, phase, count;

    count = areaFxCount[curArea];
    if (!count) return;
    if (fxCursor >= count) fxCursor = 0;
    effect = areaFx(curArea) + (u16)fxCursor * 132;
    fxCursor++;
    x = effect[0]; y = effect[1];
    if (x < cacheX || x >= cacheX + 34 || y < cacheY || y >= cacheY + 30)
        return;
    phase = (frameCounter >> 5) & 3;
    dmaCopyVram(effect + 4 + ((u16)phase << 5),
                VRAM_FIELD_GFX + (slot(x, y) << 4), 32);
}
