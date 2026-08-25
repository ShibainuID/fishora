import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // The largest source in public/ is 2400px (sea.jpg); the catch photographs
    // are 1600px or smaller. The default list tops out at 3840, so a wide
    // viewport at 2x asks the optimiser to upscale a 1600px photo to 3840. That
    // is pure waste, and on this machine the request never completed, which
    // showed up as an image that simply never appeared.
    deviceSizes: [640, 750, 828, 1080, 1200, 1600, 1920, 2048],
  },
};

export default nextConfig;
