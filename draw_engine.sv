module draw_engine(
    input logic clk,
    input logic rst_n,

    //Command interface
    input logic cmd_valid,
    output logic cmd_ready,

    input logic [5:0] cmd_x, //coordinates 0-63
    input  logic [5:0]  cmd_y,

    input  logic [6:0]  cmd_width, //dimension 0-64
    input  logic [6:0]  cmd_height,

    input  logic [7:0]  cmd_color, // RGB

    // Framebuffer write interface
    output logic fb_we,
    output logic [11:0] fb_addr, // 12 bit 4096 pixels for 64x64
    output logic [7:0]  fb_data, // a pixles color

    // Status
    output logic done
);

    typedef enum logic [1:0] {IDLE,DRAW,DONE} state_t;
    state_t state, next_state;

    logic [5:0] start_x, start_y; //captured starting coordinates
    logic [6:0] width_reg, height_reg; //captured rectangle dimensions
    logic [7:0] color_reg; //captured pixel color

    logic [6:0] x_offset; //current horizontal pixel offset
    logic [6:0] y_offset; //current vertical pixel offset

    logic [7:0] current_x, current_y; //current pixel coordinates

    // Calculate coordinates with enough width to detect values above 63.
    assign current_x = {2'b00, start_x} + {1'b0, x_offset};
    assign current_y = {2'b00, start_y} + {1'b0, y_offset};

    always_ff @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            state <= IDLE;
        end
        else begin
            state <= next_state;
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            // Reset command registers
            start_x    <= 0;
            start_y    <= 0;
            width_reg  <= 0;
            height_reg <= 0;
            color_reg  <= 0;
            // Reset x_offset and y_offset
            x_offset   <= 0;
            y_offset   <= 0;    
        end
        else if (cmd_valid && cmd_ready) begin
            // Capture command parameters
            start_x    <= cmd_x;
            start_y    <= cmd_y;
            width_reg  <= cmd_width;
            height_reg <= cmd_height;
            color_reg  <= cmd_color;
            // Initialize x_offset and y_offset
            x_offset   <= 0;
            y_offset   <= 0;
        end
        else if (state == DRAW) begin
            // Skip counter advancement when either captured dimension is zero.
            if ((width_reg == 0) || (height_reg == 0)) begin
                // Leave both offsets unchanged.
            end
            else if (x_offset == width_reg - 1) begin // end of row
                if (y_offset == height_reg - 1) begin
                    // Final pixel; hold offsets as the FSM moves to DONE.
                end
                else begin
                    x_offset <= 0; // reset x
                    y_offset <= y_offset + 1; // increment y
                end
            end
            else begin // continue within row
                x_offset <= x_offset + 1;
            end
        end
    end


    always_comb begin
        // Hold current state and use safe defaults for outputs.
        next_state = state;
        cmd_ready = (state == IDLE); // ready driven when in IDLE
        done = 1'b0;
        fb_we = 0;
        fb_addr = 0;
        fb_data = 0;
        case (state)
            IDLE : begin
                // Accept a command only if valid + ready
                if (cmd_valid && cmd_ready) begin
                    if ((cmd_width == 0) || (cmd_height == 0))
                        next_state = DONE;
                    else
                        next_state = DRAW;
                end
            end

            DRAW : begin
                // Write this pixel only when the rectangle is nonempty and in bounds.
                if ((width_reg == 0) || (height_reg == 0)) begin //zero width/height rectangle
                    fb_we = 1'b0;
                    next_state = DONE;
                end
                else begin
                    if ((current_x < 64) && (current_y < 64)) begin // coords in bounds
                        fb_we = 1'b1;
                        // Row-major framebuffer layout: 64 pixels per row.
                        // With both coordinates clipped to 0..63, concatenation is y*64+x.
                        fb_addr = {current_y[5:0], current_x[5:0]};
                        fb_data = color_reg;
                    end

                    // Finish after the final pixel offset has been reached.
                    if ((x_offset == width_reg - 1) &&
                        (y_offset == height_reg - 1)) begin
                        next_state = DONE;
                    end
                end
            end

            DONE : begin
                // Keep completion to one cycle, then return to idle.
                next_state = IDLE;
                done = 1'b1;
            end

            // default idle
            default : next_state = IDLE;

        endcase
    end

endmodule
