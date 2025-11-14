import { motion } from "motion/react";

export function AnimatedLogo({ className = "" }: { className?: string }) {
  return (
    <motion.div
      className={`${className} bg-gradient-to-r bg-clip-text text-transparent font-black tracking-tight`}
      style={{ fontFamily: '"Techno Race", "Arial Black", sans-serif', fontWeight: 'normal', fontStyle: 'italic' }}
      animate={{
        backgroundImage: [
          "linear-gradient(to right, #10b981 0%, #10b981 35%, #eab308 50%, #f43f5e 65%, #f43f5e 100%)",
          "linear-gradient(to right, #34d399 0%, #34d399 35%, #eab308 50%, #fb7185 65%, #fb7185 100%)",
          "linear-gradient(to right, #10b981 0%, #10b981 35%, #eab308 50%, #f43f5e 65%, #f43f5e 100%)",
        ],
      }}
      transition={{
        duration: 3,
        repeat: Infinity,
        ease: "easeInOut",
      }}
    >
      BullsBears
    </motion.div>
  );
}
